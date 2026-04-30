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
    payment_method: Optional[str] = None
    expense_date: datetime
    cash_session_id: Optional[int] = None
    receipt_url: Optional[str] = None


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
