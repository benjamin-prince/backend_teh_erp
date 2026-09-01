"""TEHTEK — Finance Module Models. Invoices, Payments, Cash Sessions."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index, event
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    InvoiceType, InvoiceStatus, PaymentMethod, PaymentStatus, CashSessionStatus
)


class Invoice(Base):
    __tablename__ = "invoices"

    id             = Column(Integer, primary_key=True)
    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id      = Column(Integer, ForeignKey("branches.id"), nullable=True)
    invoice_number = Column(String(30), unique=True, nullable=False)  # INV-2026-04-000001
    invoice_type   = Column(String(30), nullable=False, default=InvoiceType.shipment)
    status         = Column(String(30), nullable=False, default=InvoiceStatus.draft)

    # Customer or supplier
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=True)
    supplier_id    = Column(Integer, nullable=True)

    # Polymorphic reference
    ref_model      = Column(String(50), nullable=True)   # "shipment", "order", etc.
    ref_id         = Column(Integer, nullable=True)

    # Line items are stored as text/JSON
    line_items_json = Column(Text, nullable=True)

    subtotal       = Column(Numeric(14, 2), default=0)
    tax_amount     = Column(Numeric(14, 2), default=0)   # TVA (added)
    retenue_amount = Column(Numeric(14, 2), default=0)   # retenue à la source (withheld)
    discount_amount = Column(Numeric(14, 2), default=0)
    total          = Column(Numeric(14, 2), nullable=False)
    paid_amount    = Column(Numeric(14, 2), default=0)
    balance_due    = Column(Numeric(14, 2), nullable=False)
    # Tax status carried from the source order/project (none | tva | retenue)
    tax_type       = Column(String(20), nullable=False, default="none")
    tax_rate       = Column(Numeric(6, 3), default=0)
    # Advance/partial (acompte) invoice: % of the source total this invoice bills.
    # NULL or 100 = full invoice. subtotal stays the FULL HT for the acompte print.
    advance_pct    = Column(Numeric(6, 2), nullable=True)
    # Document terms carried from the source order/project (shown on the invoice)
    guarantee_value      = Column(Integer, nullable=True)
    guarantee_unit       = Column(String(10), nullable=True)   # week | month | year
    delivery_delay_value = Column(Integer, nullable=True)
    delivery_delay_unit  = Column(String(10), nullable=True)   # day | month

    currency       = Column(String(10), default="XAF")
    due_date       = Column(DateTime, nullable=True)
    sent_at        = Column(DateTime, nullable=True)
    paid_at        = Column(DateTime, nullable=True)
    cancelled_at   = Column(DateTime, nullable=True)
    cancel_reason  = Column(Text, nullable=True)

    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at     = Column(DateTime, nullable=True)

    payments = relationship("Payment", back_populates="invoice", lazy="select")
    __table_args__ = (
        Index("ix_invoice_company_status", "company_id", "status"),
        Index("ix_invoice_customer", "customer_id"),
    )


class InvoiceNumberLocked(Exception):
    """SEQ-002 violation: an issued invoice number was reassigned."""

    def __init__(self, old: str, new: str):
        self.old, self.new = old, new
        super().__init__(
            f"Le numéro de facture {old} est définitif et ne peut pas devenir {new}."
        )


@event.listens_for(Invoice.invoice_number, "set", retval=True, active_history=True)
def _freeze_invoice_number(target, value, oldvalue, initiator):
    """SEQ-002: a number handed to a customer is never reassigned.

    Guards every application write path — regeneration, imports, admin edits.
    The database carries the same rule as a trigger (see the SEQ-002 migration)
    so raw SQL cannot bypass it either.
    """
    if isinstance(oldvalue, str) and oldvalue and oldvalue != value:
        raise InvoiceNumberLocked(oldvalue, value)
    return value


class Payment(Base):
    __tablename__ = "payments"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    invoice_id      = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)
    payment_method  = Column(String(30), nullable=False)
    status          = Column(String(30), default=PaymentStatus.pending)
    amount          = Column(Numeric(14, 2), nullable=False)
    currency        = Column(String(10), default="XAF")
    reference       = Column(String(200), nullable=True)   # mobile money ref, bank ref
    receipt_number  = Column(String(30), nullable=True)    # RCP-2026-04-000001
    cash_session_id = Column(Integer, ForeignKey("cash_sessions.id"), nullable=True)
    notes           = Column(Text, nullable=True)
    confirmed_by    = Column(Integer, nullable=True)
    confirmed_at    = Column(DateTime, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")
    __table_args__ = (Index("ix_payment_company", "company_id"),)


class CashSession(Base):
    """Daily cash drawer sessions per staff member."""
    __tablename__ = "cash_sessions"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id       = Column(Integer, ForeignKey("branches.id"), nullable=True)
    staff_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    status          = Column(String(30), default=CashSessionStatus.open)

    opening_balance = Column(Numeric(14, 2), nullable=False)
    expected_close  = Column(Numeric(14, 2), nullable=True)  # opening + cash received
    actual_close    = Column(Numeric(14, 2), nullable=True)
    discrepancy     = Column(Numeric(14, 2), nullable=True)

    opened_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at       = Column(DateTime, nullable=True)
    approved_by     = Column(Integer, nullable=True)
    notes           = Column(Text, nullable=True)

    __table_args__ = (Index("ix_cash_session_company_status", "company_id", "status"),)


class Expense(Base):
    __tablename__ = "expenses"

    id           = Column(Integer, primary_key=True)
    company_id   = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id    = Column(Integer, ForeignKey("branches.id"), nullable=True)
    category     = Column(String(100), nullable=False)
    description  = Column(Text, nullable=False)
    amount       = Column(Numeric(14, 2), nullable=False)
    currency     = Column(String(10), default="XAF")
    payment_method = Column(String(30), nullable=True)
    receipt_url  = Column(String(500), nullable=True)
    expense_date = Column(DateTime, nullable=False)
    cash_session_id = Column(Integer, ForeignKey("cash_sessions.id"), nullable=True)
    ref_model    = Column(String(100), nullable=True)   # "container", "shipment", etc.
    ref_id       = Column(Integer,     nullable=True)
    approved_by  = Column(Integer,     nullable=True)
    created_by   = Column(Integer, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at   = Column(DateTime, nullable=True)


# ── Debt (added by install_debt.sh) ──────────────────────────────────────────

class Debt(Base):
    __tablename__ = "debts"

    id            = Column(Integer, primary_key=True)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)
    debt_number   = Column(String(30), unique=True, nullable=False)  # DBT-2026-0001
    creditor_name = Column(String(255), nullable=False)
    creditor_type = Column(String(50),  nullable=False)  # bank|supplier|landlord|individual|other
    debt_type     = Column(String(20),  nullable=False, default="loan")  # loan | recurring
    purpose       = Column(Text,        nullable=False)
    ref_model     = Column(String(100), nullable=True)
    ref_id        = Column(Integer,     nullable=True)
    ref_label     = Column(String(255), nullable=True)

    principal           = Column(Numeric(15, 2), nullable=False)
    outstanding         = Column(Numeric(15, 2), nullable=False)
    total_paid          = Column(Numeric(15, 2), nullable=False, default=0)
    installment_amount  = Column(Numeric(15, 2), nullable=False, default=0)
    interest_rate       = Column(Numeric(5,  2), nullable=True)
    currency            = Column(String(10),     nullable=False, default="XAF")

    repayment_frequency = Column(String(50),  nullable=False, default="monthly")
    start_date          = Column(DateTime,    nullable=False)
    deadline_date       = Column(DateTime,    nullable=False)
    end_date            = Column(DateTime,    nullable=True)
    next_due_date       = Column(DateTime,    nullable=True)
    last_payment_date   = Column(DateTime,    nullable=True)

    status     = Column(String(50), nullable=False, default="active")
    notes      = Column(Text,       nullable=True)
    created_by = Column(Integer,    nullable=True)
    created_at = Column(DateTime,   default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime,   nullable=True)

    debt_payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_debt_company_status", "company_id", "status"),
        Index("ix_debt_next_due_date",  "company_id", "next_due_date"),
    )


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id                 = Column(Integer,       primary_key=True)
    company_id         = Column(Integer,       ForeignKey("companies.id"), nullable=False)
    debt_id            = Column(Integer,       ForeignKey("debts.id"),     nullable=False)
    expense_id         = Column(Integer,       nullable=True)
    amount             = Column(Numeric(14, 2), nullable=False)
    payment_date       = Column(DateTime,      nullable=False)
    money_account_id   = Column(Integer,       nullable=True)
    money_account_name = Column(String(255),   nullable=True)
    payment_method     = Column(String(30),    nullable=False)
    note               = Column(Text,          nullable=True)
    created_by         = Column(Integer,       ForeignKey("users.id"), nullable=False)
    created_at         = Column(DateTime,      default=datetime.utcnow, nullable=False)

    debt = relationship("Debt", back_populates="debt_payments")
    __table_args__ = (Index("ix_debt_payment_debt_id", "debt_id"),)

