"""TEHTEK — Reminders / Scheduler.

A single lightweight table backing payment-to-receive, pickup, delivery and
custom reminders. Rows are surfaced in-app (Reminders page + header bell) and,
when due, pushed over WhatsApp best-effort by the background scheduler.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, Index

from app.core.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id           = Column(Integer, primary_key=True)
    company_id   = Column(Integer, nullable=False, default=1, index=True)

    title        = Column(String(255), nullable=False)
    # payment | pickup | delivery | custom
    type         = Column(String(20), nullable=False, default="custom")
    # pending | done | cancelled
    status       = Column(String(20), nullable=False, default="pending")
    due_at       = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Who to contact — required for manual reminders (validated at the API).
    contact_name  = Column(String(200), nullable=True)
    contact_phone = Column(String(40), nullable=True)
    # Full pickup/delivery address — optional (mainly for pickup reminders).
    address       = Column(Text, nullable=True)

    # Pickup fee — charged for the pickup service; recorded as an income
    # transaction when the pickup is confirmed.
    fee_amount    = Column(Numeric(14, 2), nullable=True)
    fee_currency  = Column(String(10), nullable=True, default="XAF")

    # Optional deep-link to the source record.
    ref_model    = Column(String(50), nullable=True)   # "shipment" | "invoice" | "customer"
    ref_id       = Column(Integer, nullable=True)
    customer_id  = Column(Integer, nullable=True)

    notes        = Column(Text, nullable=True)

    # WhatsApp push. notify_wa_to falls back to WHATSAPP_ADMIN_NOTIFY_WA_ID.
    notify_wa    = Column(Boolean, nullable=False, default=True)
    notify_wa_to = Column(String(40), nullable=True)
    notified_at  = Column(DateTime, nullable=True)     # set once pushed → dedupe

    # Auto-generation dedupe key, e.g. "invoice:25" / "pickup:18". NULL = manual.
    auto_source  = Column(String(60), nullable=True, index=True)

    # Records CREATED by confirming this reminder, so "undo" can reverse them.
    created_shipment_id = Column(Integer, nullable=True)
    created_income_id   = Column(Integer, nullable=True)
    created_payment_id  = Column(Integer, nullable=True)

    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_reminder_company_status_due", "company_id", "status", "due_at"),
    )
