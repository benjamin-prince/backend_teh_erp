"""TEHTEK — Finance Module Models. Invoices, Payments, Cash Sessions."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
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
    tax_amount     = Column(Numeric(14, 2), default=0)
    discount_amount = Column(Numeric(14, 2), default=0)
    total          = Column(Numeric(14, 2), nullable=False)
    paid_amount    = Column(Numeric(14, 2), default=0)
    balance_due    = Column(Numeric(14, 2), nullable=False)

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
    approved_by  = Column(Integer, nullable=True)
    created_by   = Column(Integer, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at   = Column(DateTime, nullable=True)
