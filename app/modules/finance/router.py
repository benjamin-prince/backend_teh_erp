"""TEHTEK — Finance Router. ACC-007: auth at router level."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.finance.models import Invoice, Payment, CashSession, Expense
from app.modules.companies.controller import next_sequence
from app.core.enums import InvoiceStatus, PaymentStatus, CashSessionStatus, SequenceType

router = APIRouter(
    prefix="/api/v1/finance",
    tags=["finance"],
    dependencies=[Depends(get_current_user)],
)


class InvoiceCreate(BaseModel):
    invoice_type: str
    customer_id: Optional[int] = None
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None
    subtotal: float
    tax_amount: float = 0
    discount_amount: float = 0
    currency: str = "XAF"
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class PaymentRecord(BaseModel):
    invoice_id: int
    payment_method: str
    amount: float
    currency: str = "XAF"
    reference: Optional[str] = None
    cash_session_id: Optional[int] = None
    notes: Optional[str] = None

class CashOpen(BaseModel):
    branch_id: Optional[int] = None
    opening_balance: float

class CashClose(BaseModel):
    actual_close: float
    notes: Optional[str] = None

class ExpenseCreate(BaseModel):
    category: str
    description: str
    amount: float
    currency: str = "XAF"
    payment_method: Optional[str] = None
    expense_date: datetime
    cash_session_id: Optional[int] = None
    receipt_url: Optional[str] = None
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.post("/invoices", status_code=201)
def create_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    number = next_sequence(db, SequenceType.invoice_number)
    total = body.subtotal + body.tax_amount - body.discount_amount
    invoice = Invoice(
        company_id=current_user.company_id,
        invoice_number=number,
        total=total,
        balance_due=total,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices")
def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    q = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.deleted_at.is_(None),
    )
    if status:
        q = q.filter(Invoice.status == status)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    return q.offset(skip).limit(limit).all()


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("finance:invoices")),
):
    inv = db.query(Invoice).filter_by(id=invoice_id, deleted_at=None).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


class InvoiceUpdate(BaseModel):
    subtotal:         Optional[float] = None
    total:            Optional[float] = None
    balance_due:      Optional[float] = None
    currency:         Optional[str]   = None
    line_items_json:  Optional[str]   = None
    notes:            Optional[str]   = None

@router.patch("/invoices/{invoice_id}")
def update_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("finance:invoices")),
):
    inv = db.query(Invoice).filter_by(id=invoice_id, deleted_at=None).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == "cancelled":
        raise HTTPException(400, "Cannot update a cancelled invoice")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(inv, k, v)
    # Recalculate status based on actual paid vs total
    paid = float(inv.paid_amount or 0)
    total = float(inv.total or 0)
    inv.balance_due = max(total - paid, 0)
    if total > 0:
        if paid >= total:
            inv.status = InvoiceStatus.paid
        elif paid > 0:
            inv.status = InvoiceStatus.partial
        else:
            inv.status = InvoiceStatus.draft
    from datetime import datetime as _dt
    inv.updated_at = _dt.utcnow()
    db.commit()
    db.refresh(inv)
    return {c.name: getattr(inv, c.name) for c in inv.__table__.columns}

@router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice(
    invoice_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:cancel_invoice")),
):
    inv = db.query(Invoice).filter_by(id=invoice_id, deleted_at=None).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.paid_amount > 0:
        raise HTTPException(400, "Cannot cancel a partially or fully paid invoice")
    inv.status = InvoiceStatus.cancelled
    inv.cancel_reason = reason
    inv.cancelled_at = datetime.utcnow()
    db.commit()
    return inv


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/payments", status_code=201)
def record_payment(
    body: PaymentRecord,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:payments")),
):
    inv = db.query(Invoice).filter_by(id=body.invoice_id, deleted_at=None).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.cancelled:
        raise HTTPException(400, "Cannot record payment on cancelled invoice")

    receipt_number = next_sequence(db, SequenceType.receipt_number)
    payment = Payment(
        company_id=current_user.company_id,
        customer_id=inv.customer_id,
        receipt_number=receipt_number,
        created_by=current_user.id,
        status=PaymentStatus.confirmed,
        confirmed_by=current_user.id,
        confirmed_at=datetime.utcnow(),
        **body.model_dump(),
    )
    db.add(payment)

    # Update invoice balances
    inv.paid_amount = float(inv.paid_amount or 0) + body.amount
    inv.balance_due = float(inv.total) - float(inv.paid_amount)
    if inv.balance_due <= 0:
        inv.status = InvoiceStatus.paid
        inv.paid_at = datetime.utcnow()
    elif inv.paid_amount > 0:
        inv.status = InvoiceStatus.partial
    inv.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:payments")),
):
    """Delete a payment and recalculate invoice status."""
    q = db.query(Payment).filter(Payment.id == payment_id)
    if not current_user.is_superadmin:
        q = q.filter(Payment.company_id == current_user.company_id)
    payment = q.first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    inv = db.query(Invoice).filter_by(id=payment.invoice_id).first()
    db.delete(payment)
    db.flush()
    if inv:
        # Recalculate from remaining payments
        from sqlalchemy import func
        total_paid = db.query(func.sum(Payment.amount)).filter_by(
            invoice_id=inv.id
        ).scalar() or 0
        inv.paid_amount = float(total_paid)
        inv.balance_due = max(float(inv.total) - inv.paid_amount, 0)
        if inv.paid_amount <= 0:
            inv.status = InvoiceStatus.draft
        elif inv.balance_due <= 0:
            inv.status = InvoiceStatus.paid
        else:
            inv.status = InvoiceStatus.partial
        inv.paid_at = None if inv.paid_amount <= 0 else inv.paid_at
        inv.updated_at = datetime.utcnow()
    db.commit()


@router.get("/payments")
def list_payments(
    invoice_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:payments")),
):
    q = db.query(Payment).filter_by(company_id=current_user.company_id)
    if invoice_id:
        q = q.filter(Payment.invoice_id == invoice_id)
    return q.offset(skip).limit(limit).all()


# ── Cash Sessions ─────────────────────────────────────────────────────────────

@router.post("/cash-sessions/open", status_code=201)
def open_cash_session(
    body: CashOpen,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("pos:cash_session")),
):
    # Only one open session per staff
    existing = db.query(CashSession).filter_by(
        staff_id=current_user.id,
        status=CashSessionStatus.open,
    ).first()
    if existing:
        raise HTTPException(400, "You already have an open cash session")
    session = CashSession(
        company_id=current_user.company_id,
        branch_id=body.branch_id or current_user.branch_id,
        staff_id=current_user.id,
        opening_balance=body.opening_balance,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/cash-sessions/{session_id}/close")
def close_cash_session(
    session_id: int,
    body: CashClose,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("pos:cash_session")),
):
    s = db.query(CashSession).filter_by(id=session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    if s.staff_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(403, "This is not your cash session")
    s.actual_close = body.actual_close
    s.discrepancy = float(s.expected_close or s.opening_balance) - body.actual_close
    s.closed_at = datetime.utcnow()
    s.notes = body.notes
    s.status = (
        CashSessionStatus.discrepancy_flagged
        if abs(float(s.discrepancy)) > 0
        else CashSessionStatus.closed
    )
    db.commit()
    return s


@router.get("/cash-sessions")
def list_cash_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:cash_sessions")),
):
    return db.query(CashSession).filter_by(company_id=current_user.company_id).all()


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.post("/expenses", status_code=201)
def create_expense(
    body: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:expenses")),
):
    expense = Expense(
        company_id=current_user.company_id,
        branch_id=current_user.branch_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/expenses")
def list_expenses(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:expenses")),
):
    return db.query(Expense).filter(
        Expense.company_id == current_user.company_id,
        Expense.deleted_at.is_(None),
    ).offset(skip).limit(limit).all()


class OrderInvoiceGen(BaseModel):
    percentage: Optional[float] = None   # 1..100 — share of the order to bill
    amount: Optional[float] = None       # explicit amount to bill (acompte)


@router.post("/orders/{order_id}/invoice", status_code=201)
def generate_invoice_from_order(
    order_id: int,
    body: Optional[OrderInvoiceGen] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    """Generate a (possibly partial / acompte) invoice for an order.

    Like service projects: bills a percentage or amount, supports multiple
    tranches until fully paid, and returns the current open (unpaid) invoice
    instead of creating a duplicate.
    """
    from app.modules.orders.models import Order as OrderModel
    import json as _json
    o = db.query(OrderModel).filter_by(id=order_id, deleted_at=None).first()
    if not o:
        raise HTTPException(404, "Order not found")

    pct = body.percentage if body else None
    amt = body.amount if body else None

    all_invs = db.query(Invoice).filter_by(ref_model="order", ref_id=order_id, deleted_at=None).all()
    # One open tranche at a time — return it instead of duplicating
    open_unpaid = next(
        (i for i in sorted(all_invs, key=lambda x: x.id, reverse=True)
         if i.status != "cancelled" and float(i.paid_amount or 0) == 0),
        None,
    )
    if open_unpaid is not None:
        return open_unpaid

    order_total = float(o.total or 0)
    total_paid = sum(float(i.paid_amount or 0) for i in all_invs)
    remaining = max(order_total - total_paid, 0.0)
    # Nothing left to bill — return the latest invoice instead of re-billing
    if remaining <= 0.009 and all_invs:
        return sorted(all_invs, key=lambda x: x.id, reverse=True)[0]

    if amt is not None:
        inv_total = min(float(amt), remaining if remaining > 0 else order_total)
        factor = (inv_total / order_total) if order_total > 0 else 1.0
    elif pct is not None:
        factor = min(max(float(pct), 1.0), 100.0) / 100.0
        inv_total = order_total * factor
    else:
        inv_total = remaining if remaining > 0 else order_total
        factor = (inv_total / order_total) if order_total > 0 else 1.0
    inv_total = round(inv_total, 2)
    pct_display = round(factor * 100, 2)

    line_items = [
        {"description": item.description or "", "quantity": float(item.quantity),
         "unit_price": float(item.unit_price), "total": float(item.line_total)}
        for item in (o.items or [])
    ]
    notes_parts = []
    if pct_display < 99.99:
        notes_parts.append(f"Facture partielle : {round(pct_display)}% du montant total de la commande.")
    if total_paid > 0:
        cur = o.currency or "XAF"
        notes_parts.append(f"Déjà facturé et payé : {int(total_paid):,} {cur}".replace(",", " "))
    if o.notes:
        notes_parts.append(o.notes)
    notes = "\n".join(notes_parts) or None

    inv = Invoice(
        company_id=current_user.company_id,
        invoice_number=next_sequence(db, SequenceType.invoice_number),
        invoice_type="sale",
        customer_id=o.customer_id,
        ref_model="order",
        ref_id=o.id,
        subtotal=float(o.subtotal or 0),                       # FULL HT (acompte print shows complet)
        tax_amount=round(float(o.tax_amount or 0) * factor, 2),
        retenue_amount=round(float(getattr(o, "retenue_amount", 0) or 0) * factor, 2),
        discount_amount=round(float(o.discount_amount or 0) * factor, 2),
        total=inv_total,
        balance_due=inv_total,
        tax_type=getattr(o, "tax_type", "none") or "none",
        tax_rate=float(getattr(o, "tax_rate", 0) or 0),
        advance_pct=(pct_display if pct_display < 99.99 else None),
        notes=notes,
        line_items_json=_json.dumps(line_items),
        created_by=current_user.id,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv

@router.get("/orders/{order_id}/invoice")
def get_invoice_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("finance:invoices")),
):
    inv = (db.query(Invoice).filter_by(ref_model="order", ref_id=order_id, deleted_at=None)
             .order_by(Invoice.id.desc()).first())
    if not inv:
        raise HTTPException(404, "No invoice for this order")
    return inv


# ── Debt (added by install_debt.sh) ──────────────────────────────────────────

from app.modules.finance.models import Debt, DebtPayment


class DebtCreate(BaseModel):
    creditor_name:       str
    creditor_type:       str                    # bank|supplier|landlord|individual|other
    debt_type:           str             = "loan"   # loan | recurring
    purpose:             str
    ref_model:           Optional[str]  = None
    ref_id:              Optional[int]  = None
    ref_label:           Optional[str]  = None
    principal:           float
    outstanding:         Optional[float] = None
    monthly_payment:     Optional[float] = None  # frontend alias → installment_amount
    installment_amount:  Optional[float] = None
    interest_rate:       Optional[float] = None
    currency:            str             = "XAF"
    repayment_frequency: str             = "monthly"
    start_date:          datetime
    end_date:            Optional[datetime] = None  # frontend alias → deadline_date
    deadline_date:       Optional[datetime] = None
    next_due_date:       Optional[datetime] = None
    status:              str             = "active"
    notes:               Optional[str]   = None


class DebtUpdate(BaseModel):
    creditor_name:       Optional[str]      = None
    creditor_type:       Optional[str]      = None
    debt_type:           Optional[str]      = None
    purpose:             Optional[str]      = None
    ref_model:           Optional[str]      = None
    ref_label:           Optional[str]      = None
    outstanding:         Optional[float]    = None
    monthly_payment:     Optional[float]    = None
    installment_amount:  Optional[float]    = None
    interest_rate:       Optional[float]    = None
    repayment_frequency: Optional[str]      = None
    end_date:            Optional[datetime] = None
    deadline_date:       Optional[datetime] = None
    next_due_date:       Optional[datetime] = None
    status:              Optional[str]      = None
    notes:               Optional[str]      = None


class DebtPaymentCreate(BaseModel):
    amount:         float
    notes:          Optional[str] = None
    payment_method: str           = "bank_transfer"
    reference:      Optional[str] = None


def _debt_number(db: Session) -> str:
    from sqlalchemy import extract
    from sqlalchemy import func as _f
    year = datetime.utcnow().year
    n = db.query(_f.count(Debt.id)).filter(
        extract("year", Debt.created_at) == year
    ).scalar() or 0
    return f"DBT-{year}-{str(n + 1).zfill(4)}"


@router.get("/debt")
def list_debts(
    status: Optional[str] = None,
    skip:   int = 0,
    limit:  int = 100,
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    q = db.query(Debt).filter(
        Debt.company_id == current_user.company_id,
        Debt.deleted_at.is_(None),
    )
    if status:
        q = q.filter(Debt.status == status)
    return (
        q.order_by(Debt.next_due_date.asc().nulls_last(), Debt.created_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.post("/debt", status_code=201)
def create_debt(
    body: DebtCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    installment = body.installment_amount or body.monthly_payment or 0
    deadline    = body.deadline_date or body.end_date
    if not deadline:
        raise HTTPException(400, "deadline_date (or end_date) is required")
    outstanding = body.outstanding if body.outstanding is not None else body.principal
    d = Debt(
        company_id=current_user.company_id,
        debt_number=_debt_number(db),
        creditor_name=body.creditor_name,
        creditor_type=body.creditor_type,
        debt_type=body.debt_type,
        purpose=body.purpose,
        ref_model=body.ref_model,
        ref_id=body.ref_id,
        ref_label=body.ref_label,
        principal=body.principal,
        outstanding=outstanding,
        total_paid=0,
        installment_amount=installment,
        interest_rate=body.interest_rate,
        currency=body.currency,
        repayment_frequency=body.repayment_frequency,
        start_date=body.start_date,
        deadline_date=deadline,
        end_date=body.end_date,
        next_due_date=body.next_due_date,
        status=body.status,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.get("/debt/{debt_id}")
def get_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    return d


@router.patch("/debt/{debt_id}")
def update_debt(
    debt_id: int,
    body: DebtUpdate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    patch = body.model_dump(exclude_unset=True)
    # Resolve aliases
    if "monthly_payment" in patch and "installment_amount" not in patch:
        patch["installment_amount"] = patch.pop("monthly_payment")
    else:
        patch.pop("monthly_payment", None)
    if "end_date" in patch and "deadline_date" not in patch:
        patch["deadline_date"] = patch.pop("end_date")
    for k, v in patch.items():
        if hasattr(d, k):
            setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.delete("/debt/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    d.deleted_at = datetime.utcnow()
    db.commit()


@router.post("/debt/{debt_id}/payment")
def record_debt_payment(
    debt_id: int,
    body: DebtPaymentCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    pay = DebtPayment(
        debt_id=d.id,
        payment_date=datetime.utcnow(),
        amount=body.amount,
        payment_method=body.payment_method,
        reference=body.reference,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(pay)
    d.outstanding       = max(0, float(d.outstanding) - body.amount)
    d.total_paid        = float(d.total_paid or 0) + body.amount
    d.last_payment_date = datetime.utcnow()
    if d.outstanding <= 0:
        d.status = "paid_off"
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.get("/debt/{debt_id}/payments")
def list_debt_payments(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    return (
        db.query(DebtPayment)
        .filter_by(debt_id=d.id)
        .order_by(DebtPayment.payment_date.desc())
        .all()
    )
