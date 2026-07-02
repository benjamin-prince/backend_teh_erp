"""TEHTEK — Orders Router. ACC-007: auth at router level."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.security import verify_password
from app.modules.orders.models import Order, OrderItem, Exception_
from app.modules.companies.controller import next_sequence
from app.core.enums import OrderStatus, SequenceType, ExceptionStatus

router = APIRouter(
    prefix="/api/v1",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


def compute_tax(raw_subtotal: float, tax_type: Optional[str], tax_rate: float,
                price_inclusive: bool, discount: float):
    """Compute (subtotal_HT, tax_amount, retenue_amount, total) for one tax type.

    - none    : total = subtotal − discount
    - tva     : added (HT) or extracted (TTC, price_inclusive); total = HT + TVA − discount
    - retenue : withheld; total (net à payer) = subtotal − retenue − discount
    """
    rate = float(tax_rate or 0) / 100.0
    disc = float(discount or 0)
    tt = (tax_type or "none").lower()
    if tt == "tva":
        if price_inclusive and rate:
            subtotal = round(raw_subtotal / (1 + rate), 2)
            tax = round(raw_subtotal - subtotal, 2)
        else:
            subtotal = round(raw_subtotal, 2)
            tax = round(raw_subtotal * rate, 2)
        retenue = 0.0
        total = subtotal + tax - disc
    elif tt == "retenue":
        subtotal = round(raw_subtotal, 2)
        tax = 0.0
        retenue = round(raw_subtotal * rate, 2)
        total = subtotal - retenue - disc
    else:
        subtotal = round(raw_subtotal, 2)
        tax = 0.0
        retenue = 0.0
        total = subtotal - disc
    return subtotal, tax, retenue, round(total, 2)


class OrderItemIn(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: int
    unit_price: float
    serials: Optional[str] = None   # IMEI / SN / MAC, one per line

class OrderCreate(BaseModel):
    customer_id: int
    order_type: str = "sale_order"
    currency: str = "XAF"
    items: List[OrderItemIn]
    tax_type: str = "none"          # none | tva | retenue
    tax_rate: float = 0             # percent
    price_inclusive: bool = False   # entered unit prices already include TVA (TTC)
    discount_amount: float = 0
    guarantee_value: Optional[int] = None
    guarantee_unit: Optional[str] = None            # week | month | year
    delivery_delay_value: Optional[int] = None
    delivery_delay_unit: Optional[str] = None       # day | month
    delivery_address: Optional[str] = None
    notes: Optional[str] = None

class ExceptionCreate(BaseModel):
    exception_type: str
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None
    description: str
    assigned_to: Optional[int] = None


@router.post("/orders", status_code=201)
def create_order(
    body: OrderCreate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("orders:create")),
):
    """OR-001: total = subtotal + TVA − retenue − discount."""
    order_number = next_sequence(db, SequenceType.order_number)
    raw = sum(i.quantity * i.unit_price for i in body.items)
    subtotal, tax, retenue, total = compute_tax(
        raw, body.tax_type, body.tax_rate, body.price_inclusive, body.discount_amount)

    order = Order(
        company_id=current_user.company_id,
        order_number=order_number,
        customer_id=body.customer_id,
        order_type=body.order_type,
        currency=body.currency,
        subtotal=subtotal,
        tax_amount=tax,
        retenue_amount=retenue,
        discount_amount=body.discount_amount,
        total=total,
        tax_type=body.tax_type,
        tax_rate=body.tax_rate,
        price_inclusive=body.price_inclusive,
        guarantee_value=body.guarantee_value,
        guarantee_unit=body.guarantee_unit,
        delivery_delay_value=body.delivery_delay_value,
        delivery_delay_unit=body.delivery_delay_unit,
        delivery_address=body.delivery_address,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()
    for item in body.items:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.quantity * item.unit_price,
            serials=item.serials,
        ))
    db.commit()
    db.refresh(order)
    return order

@router.get("/orders")
def list_orders(
    status: Optional[str] = None, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("orders:read")),
):
    q = db.query(Order).filter(
        Order.company_id == current_user.company_id, Order.deleted_at.is_(None)
    )
    if status:
        q = q.filter(Order.status == status)
    orders = q.offset(skip).limit(limit).all()
    # Attach payment info (from linked invoices) so the UI can show a money recap
    # and drop delivered + fully-paid orders out of the active list.
    from app.modules.finance.models import Invoice
    ids = [o.id for o in orders]
    paid_by, inv_total_by = {}, {}
    if ids:
        invs = db.query(Invoice).filter(
            Invoice.ref_model == "order", Invoice.ref_id.in_(ids)
        ).all()
        for inv in invs:
            paid_by[inv.ref_id] = paid_by.get(inv.ref_id, 0.0) + float(inv.paid_amount or 0)
            inv_total_by[inv.ref_id] = inv_total_by.get(inv.ref_id, 0.0) + float(inv.total or 0)
    for o in orders:
        paid = paid_by.get(o.id, 0.0)
        o.paid_amount = round(paid, 2)
        o.balance_due = round(max(float(o.total or 0) - paid, 0.0), 2)
        o.fully_paid = inv_total_by.get(o.id, 0.0) > 0 and o.balance_due <= 0.009
    return orders

@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), _=Depends(require_permission("orders:read"))):
    o = db.query(Order).filter_by(id=order_id, deleted_at=None).first()
    if not o:
        raise HTTPException(404, "Order not found")
    _ = o.items  # force lazy load
    return o

@router.post("/orders/{order_id}/confirm")
def confirm_order(
    order_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("orders:approve")),
):
    o = db.query(Order).filter_by(id=order_id).first()
    if not o:
        raise HTTPException(404, "Order not found")
    o.status = OrderStatus.proforma_sent
    o.updated_at = datetime.utcnow()
    db.commit()
    return o

# ── Exceptions ─────────────────────────────────────────────────────────────────

@router.post("/exceptions", status_code=201)
def create_exception(
    body: ExceptionCreate, db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    exc = Exception_(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc

@router.get("/exceptions")
def list_exceptions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("exceptions:read")),
):
    q = db.query(Exception_).filter_by(company_id=current_user.company_id)
    if status:
        q = q.filter(Exception_.status == status)
    return q.all()

@router.post("/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: int,
    resolution: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("exceptions:resolve")),
):
    exc = db.query(Exception_).filter_by(id=exception_id).first()
    if not exc:
        raise HTTPException(404, "Exception not found")
    exc.status = ExceptionStatus.resolved
    exc.resolution = resolution
    exc.resolved_by = current_user.id
    exc.resolved_at = datetime.utcnow()
    db.commit()
    return exc


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    apply_tva: Optional[bool] = None          # legacy toggle → maps to tax_type
    tax_type: Optional[str] = None            # none | tva | retenue
    tax_rate: Optional[float] = None          # percent
    price_inclusive: Optional[bool] = None
    discount_amount: Optional[float] = None
    delivered: Optional[bool] = None           # independent fulfilment flag
    guarantee_value: Optional[int] = None
    guarantee_unit: Optional[str] = None
    delivery_delay_value: Optional[int] = None
    delivery_delay_unit: Optional[str] = None
    notes: Optional[str] = None
    delivery_address: Optional[str] = None
    items: Optional[List[OrderItemIn]] = None  # full replacement of line items

class SkipBrBody(BaseModel):
    reason: str

@router.patch("/orders/{order_id}")
def update_order(
    order_id: int, body: OrderUpdate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("orders:update")),
):
    o = db.query(Order).filter_by(id=order_id, deleted_at=None).first()
    if not o:
        raise HTTPException(404, "Order not found")
    recompute = False

    if body.items is not None:
        if len(body.items) == 0:
            raise HTTPException(400, "An order must keep at least one item")
        o.items.clear()          # delete-orphan removes the previous lines
        db.flush()
        for it in body.items:
            o.items.append(OrderItem(
                product_id=it.product_id,
                description=it.description,
                quantity=it.quantity,
                unit_price=it.unit_price,
                line_total=it.quantity * it.unit_price,
                serials=it.serials,
            ))
        recompute = True

    # Legacy apply_tva → tax_type/tax_rate
    if body.apply_tva is not None:
        o.tax_type = "tva" if body.apply_tva else "none"
        o.tax_rate = 19.25 if body.apply_tva else 0
        recompute = True
    if body.tax_type is not None:
        o.tax_type = body.tax_type
        recompute = True
    if body.tax_rate is not None:
        o.tax_rate = body.tax_rate
        recompute = True
    if body.price_inclusive is not None:
        o.price_inclusive = body.price_inclusive
        recompute = True
    if body.discount_amount is not None:
        o.discount_amount = body.discount_amount
        recompute = True

    if recompute:
        raw = sum(float(i.quantity) * float(i.unit_price) for i in o.items)
        subtotal, tax, retenue, total = compute_tax(
            raw, o.tax_type, float(o.tax_rate or 0), bool(o.price_inclusive),
            float(o.discount_amount or 0))
        o.subtotal, o.tax_amount, o.retenue_amount, o.total = subtotal, tax, retenue, total
        # Keep a still-draft, unpaid invoice in sync so its document reflects the tax
        from app.modules.finance.models import Invoice
        inv = (db.query(Invoice)
                 .filter_by(ref_model="order", ref_id=o.id)
                 .order_by(Invoice.id.desc()).first())
        if inv and inv.status == "draft" and float(inv.paid_amount or 0) == 0:
            inv.subtotal = subtotal
            inv.tax_amount = tax
            inv.retenue_amount = retenue
            inv.discount_amount = o.discount_amount
            inv.total = total
            inv.balance_due = total
            inv.tax_type = o.tax_type
            inv.tax_rate = o.tax_rate

    if body.status is not None:
        valid = ["draft","proforma_sent","confirmed","bl_sent","br_received","invoiced","invoice_sent","delivered","cancelled"]
        if body.status not in valid:
            raise HTTPException(400, f"Invalid status: {body.status}")
        o.status = body.status
    if body.delivered is not None:
        o.delivered = body.delivered
        o.delivered_at = datetime.utcnow() if body.delivered else None
    if body.notes is not None:
        o.notes = body.notes
    if body.delivery_address is not None:
        o.delivery_address = body.delivery_address
    for f in ("guarantee_value", "guarantee_unit", "delivery_delay_value", "delivery_delay_unit"):
        v = getattr(body, f)
        if v is not None:
            setattr(o, f, v or None)
            # Keep the linked invoice's document terms in sync
            from app.modules.finance.models import Invoice
            inv2 = (db.query(Invoice)
                      .filter_by(ref_model="order", ref_id=o.id)
                      .order_by(Invoice.id.desc()).first())
            if inv2 is not None:
                setattr(inv2, f, v or None)
    o.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(o)
    _ = o.items  # force lazy load so the response includes line items
    return o

@router.post("/orders/{order_id}/skip-br")
def skip_br(
    order_id: int, body: SkipBrBody, db: Session = Depends(get_db),
    current_user=Depends(require_permission("orders:approve")),
):
    o = db.query(Order).filter_by(id=order_id, deleted_at=None).first()
    if not o:
        raise HTTPException(404, "Order not found")
    o.skip_br = True
    o.skip_br_reason = body.reason
    o.skip_br_approved_by = current_user.id
    o.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(o)
    return o


class DeleteOrderBody(BaseModel):
    password: str

@router.delete("/orders/{order_id}", status_code=204)
def delete_order(
    order_id: int,
    body: DeleteOrderBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a cancelled order after password confirmation."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Incorrect password")
    order = db.query(Order).filter_by(id=order_id, company_id=current_user.company_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.cancelled:
        raise HTTPException(400, "Only cancelled orders can be deleted")
    db.delete(order)
    db.commit()
