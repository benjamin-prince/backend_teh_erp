"""TEHTEK — Stock Module Models."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import ProductCondition, ReservationStatus, SerialStatus, StockCategory, StockStatus


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    sku = Column(String(100), nullable=True)
    barcode = Column(String(100), nullable=True)
    model_number = Column(String(100), nullable=True)

    name = Column(String(300), nullable=False)
    name_fr = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True)

    category = Column(String(50), nullable=False, default=StockCategory.electronics)
    subcategory = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)

    unit = Column(String(20), default="pcs")
    weight_kg = Column(Numeric(8, 3), nullable=True)

    cost_price = Column(Numeric(14, 2), nullable=True)
    sell_price = Column(Numeric(14, 2), nullable=True)
    tax_rate = Column(Numeric(5, 2), default=19.25)

    reorder_level = Column(Integer, default=5)
    min_order_qty = Column(Integer, default=1)
    warranty_months = Column(Integer, nullable=True)

    condition = Column(String(20), nullable=False, default=ProductCondition.new)

    is_active = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)

    # ── Shop / Website ─────────────────────────────────────────────────────
    is_published = Column(Boolean, nullable=False, default=False)  # shown on tehtek.com
    is_featured  = Column(Boolean, nullable=False, default=False)  # in "featured" section
    compare_price = Column(Numeric(14, 2), nullable=True)  # crossed-out "was" price

    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    stock_items = relationship("StockItem", back_populates="product", lazy="select")
    batches     = relationship("SupplierBatch", back_populates="product", lazy="select")
    serials     = relationship("SerialNumber",  back_populates="product", lazy="select")

    __table_args__ = (
        Index("ix_product_company", "company_id"),
        Index("ix_product_subcategory", "company_id", "category", "subcategory"),
    )


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    stock_items = relationship("StockItem", back_populates="warehouse", lazy="select")


class StockItem(Base):
    __tablename__ = "stock_items"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)

    quantity = Column(Integer, default=0, nullable=False)
    reserved_qty = Column(Integer, default=0, nullable=False)
    min_quantity = Column(Integer, default=5, nullable=False)
    status = Column(String(30), default=StockStatus.in_stock)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="stock_items")
    warehouse = relationship("Warehouse", back_populates="stock_items")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_stock_non_negative"),
        CheckConstraint("reserved_qty >= 0", name="chk_reserved_non_negative"),
    )

    @property
    def available_qty(self) -> int:
        return self.quantity - self.reserved_qty


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    movement_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    reference_id = Column(Integer, nullable=True)

    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    order_id = Column(Integer, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    status = Column(String(30), default=ReservationStatus.active)

    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Batch & Serial Traceability ───────────────────────────────────────────────

class SupplierBatch(Base):
    """One receiving event from a supplier (BCH-2026-000001)."""
    __tablename__ = "supplier_batches"

    id            = Column(Integer, primary_key=True)
    batch_number  = Column(String(50), unique=True, nullable=False, index=True)
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=False)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)

    supplier_name = Column(String(200), nullable=True)
    quantity      = Column(Integer, nullable=False)
    unit_cost     = Column(Numeric(14, 2), nullable=True)
    received_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes         = Column(Text, nullable=True)

    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="batches")
    serials = relationship("SerialNumber", back_populates="batch")

    __table_args__ = (
        Index("ix_batch_company_product", "company_id", "product_id"),
    )


class SerialNumber(Base):
    """One physical unit — manufacturer serial or TEHTEK-generated (SN-2026-XXXXXXXX)."""
    __tablename__ = "serial_numbers"

    id            = Column(Integer, primary_key=True)
    serial_number = Column(String(150), unique=True, nullable=False, index=True)
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id      = Column(Integer, ForeignKey("supplier_batches.id"), nullable=True)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_generated  = Column(Boolean, nullable=False, default=False)
    status        = Column(Enum(SerialStatus), nullable=False, default=SerialStatus.in_stock)

    # Sale
    customer_id   = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(200), nullable=True)
    sold_at       = Column(DateTime, nullable=True)

    # Return
    returned_at   = Column(DateTime, nullable=True)
    return_reason = Column(Text, nullable=True)

    notes      = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    product  = relationship("Product", back_populates="serials")
    batch    = relationship("SupplierBatch", back_populates="serials")
    customer = relationship("Customer", foreign_keys=[customer_id])

    __table_args__ = (
        Index("ix_serial_company", "company_id"),
        Index("ix_serial_product", "product_id"),
        Index("ix_serial_status",  "status"),
    )
