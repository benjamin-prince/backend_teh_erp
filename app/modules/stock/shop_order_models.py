"""
TEHTEK Shop — Order model for public e-commerce orders.
Separate from the internal ERP Order model (which requires company_id / customer_id).
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from app.core.database import Base


class ShopOrder(Base):
    __tablename__ = "shop_orders"

    id               = Column(Integer, primary_key=True)
    order_ref        = Column(String(30), unique=True, nullable=False)  # SHOP-2026-000001

    # ── Customer contact ───────────────────────────────────────────────────
    customer_name    = Column(String(200), nullable=False)
    customer_phone   = Column(String(30),  nullable=False)
    customer_email   = Column(String(255), nullable=True)
    customer_city    = Column(String(100), nullable=True)
    delivery_address = Column(Text,        nullable=True)
    delivery_notes   = Column(Text,        nullable=True)

    # ── Items (JSON snapshot) ──────────────────────────────────────────────
    # [{id, sku, name, qty, unit_price, line_total}]
    items_json       = Column(Text, nullable=False)
    subtotal         = Column(Numeric(14, 2), nullable=False)

    # ── Payment ───────────────────────────────────────────────────────────
    # method: fapshi | paypal | cod
    payment_method   = Column(String(30), nullable=False)
    # status: pending | paid | failed | expired | cod_pending | cancelled
    payment_status   = Column(String(30), nullable=False, default="pending")
    # gateway transaction reference
    payment_ref      = Column(String(200), nullable=True)
    # amount confirmed by gateway (may differ from subtotal for PayPal/FX)
    payment_amount   = Column(Numeric(14, 2), nullable=True)

    # ── Order status ──────────────────────────────────────────────────────
    # pending | confirmed | processing | shipped | delivered | cancelled
    status           = Column(String(30), nullable=False, default="pending")

    # ── COD — link to verified ERP customer (nullable) ────────────────────
    cod_customer_id  = Column(Integer, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow,
                              onupdate=datetime.utcnow, nullable=False)
