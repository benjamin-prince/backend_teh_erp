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


class OrderItemIn(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    customer_id: int
    order_type: str = "sale_order"
    currency: str = "XAF"
    items: List[OrderItemIn]
    tax_amount: float = 0
    discount_amount: float = 0
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
    """OR-001: total = sum(items) + tax - discount."""
    order_number = next_sequence(db, SequenceType.order_number)
    subtotal = sum(i.quantity * i.unit_price for i in body.items)
    total = subtotal + body.tax_amount - body.discount_amount

    order = Order(
        company_id=current_user.company_id,
        order_number=order_number,
        customer_id=body.customer_id,
        order_type=body.order_type,
        currency=body.currency,
        subtotal=subtotal,
        tax_amount=body.tax_amount,
        discount_amount=body.discount_amount,
        total=total,
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
    return q.offset(skip).limit(limit).all()

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
    apply_tva: Optional[bool] = None
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
    # OR-001: editing line items recomputes subtotal/total; TVA state is preserved.
    if body.items is not None:
        if len(body.items) == 0:
            raise HTTPException(400, "An order must keep at least one item")
        had_tva = float(o.tax_amount or 0) > 0
        o.items.clear()          # delete-orphan removes the previous lines
        db.flush()
        subtotal = 0.0
        for it in body.items:
            line = it.quantity * it.unit_price
            subtotal += line
            o.items.append(OrderItem(
                product_id=it.product_id,
                description=it.description,
                quantity=it.quantity,
                unit_price=it.unit_price,
                line_total=line,
            ))
        o.subtotal = subtotal
        o.tax_amount = round(subtotal * 0.1925, 2) if had_tva else 0
        o.total = subtotal + float(o.tax_amount) - float(o.discount_amount or 0)
    if body.status is not None:
        valid = ["draft","proforma_sent","confirmed","bl_sent","br_received","invoiced","delivered","cancelled"]
        if body.status not in valid:
            raise HTTPException(400, f"Invalid status: {body.status}")
        o.status = body.status
    if body.apply_tva is not None:
        subtotal = float(o.subtotal or 0)
        o.tax_amount = round(subtotal * 0.1925, 2) if body.apply_tva else 0
        o.total = subtotal + float(o.tax_amount) - float(o.discount_amount or 0)
    if body.notes is not None:
        o.notes = body.notes
    if body.delivery_address is not None:
        o.delivery_address = body.delivery_address
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
