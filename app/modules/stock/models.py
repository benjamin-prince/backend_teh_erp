"""TEHTEK — Stock Module Models. Rules: STK-001 to STK-007."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, CheckConstraint, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import StockCategory, StockStatus, StockMovementType, ReservationStatus


class Product(Base):
    __tablename__ = "products"

    id           = Column(Integer, primary_key=True)
    company_id   = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku          = Column(String(100), nullable=True)
    name         = Column(String(300), nullable=False)
    description  = Column(Text, nullable=True)
    category     = Column(String(50), nullable=False, default=StockCategory.electronics)
    brand        = Column(String(100), nullable=True)
    unit         = Column(String(20), default="piece")
    cost_price   = Column(Numeric(14, 2), nullable=True)
    sell_price   = Column(Numeric(14, 2), nullable=True)
    is_active    = Column(Boolean, default=True)
    image_url    = Column(String(500), nullable=True)
    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)

    stock_items  = relationship("StockItem", back_populates="product", lazy="select")
    __table_args__ = (Index("ix_product_company", "company_id"),)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id         = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id  = Column(Integer, ForeignKey("branches.id"), nullable=True)
    name       = Column(String(200), nullable=False)
    address    = Column(Text, nullable=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    stock_items = relationship("StockItem", back_populates="warehouse", lazy="select")


class StockItem(Base):
    __tablename__ = "stock_items"

    id           = Column(Integer, primary_key=True)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity     = Column(Integer, default=0, nullable=False)
    reserved_qty = Column(Integer, default=0, nullable=False)
    min_quantity = Column(Integer, default=5, nullable=False)   # STK-004 alert threshold
    status       = Column(String(30), default=StockStatus.in_stock)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # STK-001: quantity >= 0 enforced at DB level
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_stock_non_negative"),
        CheckConstraint("reserved_qty >= 0", name="chk_reserved_non_negative"),
    )

    product   = relationship("Product", back_populates="stock_items")
    warehouse = relationship("Warehouse", back_populates="stock_items")

    @property
    def available_qty(self) -> int:
        return self.quantity - self.reserved_qty


class StockMovement(Base):
    """STK-002: every movement requires a reason and staff member."""
    __tablename__ = "stock_movements"

    id           = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    movement_type = Column(String(50), nullable=False)
    quantity     = Column(Integer, nullable=False)
    reason       = Column(Text, nullable=False)   # NOT NULL — STK-002
    reference_id = Column(Integer, nullable=True)  # order_id, shipment_id, etc.
    created_by   = Column(Integer, nullable=False)  # NOT NULL — STK-002
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


class Reservation(Base):
    """STK-005: expires 24h after creation if unpaid. STK-006: paid reservations protected."""
    __tablename__ = "reservations"

    id           = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    order_id     = Column(Integer, nullable=True)
    customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=False)
    quantity     = Column(Integer, nullable=False)
    status       = Column(String(30), default=ReservationStatus.active)
    expires_at   = Column(DateTime, nullable=False)  # created_at + 24h
    paid_at      = Column(DateTime, nullable=True)   # STK-006: set when paid
    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
