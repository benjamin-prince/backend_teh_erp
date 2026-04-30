"""TEHTEK — Orders Module Models. Rules: OR-001 to OR-004."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, CheckConstraint, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import OrderType, OrderStatus, ExceptionType, ExceptionStatus


class Order(Base):
    __tablename__ = "orders"

    id            = Column(Integer, primary_key=True)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)
    order_number  = Column(String(30), unique=True, nullable=False)  # ORD-2026-000001
    customer_id   = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_type    = Column(String(30), nullable=False, default=OrderType.sale_order)
    status        = Column(String(30), nullable=False, default=OrderStatus.draft)
    supplier_id   = Column(Integer, nullable=True)  # for purchase orders
    supplier_ref_number = Column(String(100), nullable=True)  # OR-003

    # Financials — OR-001: total = sum(items) + tax - discount
    subtotal      = Column(Numeric(14, 2), default=0)
    tax_amount    = Column(Numeric(14, 2), default=0)
    discount_amount = Column(Numeric(14, 2), default=0)
    total         = Column(Numeric(14, 2), default=0)

    # Special orders (STK-007)
    deposit_amount = Column(Numeric(14, 2), nullable=True)
    deposit_paid  = Column(Boolean, default=False)

    delivery_address = Column(Text, nullable=True)
    notes         = Column(Text, nullable=True)
    created_by    = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at    = Column(DateTime, nullable=True)

    items = relationship("OrderItem", back_populates="order", lazy="select")
    __table_args__ = (Index("ix_order_company_status", "company_id", "status"),)


class OrderItem(Base):
    __tablename__ = "order_items"

    id         = Column(Integer, primary_key=True)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    description = Column(String(300), nullable=False)
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    line_total = Column(Numeric(14, 2), nullable=False)

    order = relationship("Order", back_populates="items")


class Exception_(Base):
    """Operational exceptions across all modules."""
    __tablename__ = "exceptions"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    exception_type  = Column(String(50), nullable=False)
    status          = Column(String(30), default=ExceptionStatus.open)
    ref_model       = Column(String(50), nullable=True)   # "shipment", "order", etc.
    ref_id          = Column(Integer, nullable=True)
    description     = Column(Text, nullable=False)
    resolution      = Column(Text, nullable=True)
    assigned_to     = Column(Integer, nullable=True)
    resolved_by     = Column(Integer, nullable=True)
    resolved_at     = Column(DateTime, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_exception_company_status", "company_id", "status"),)
