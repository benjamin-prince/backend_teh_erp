# # """TEHTEK — Stock Module Models. Rules: STK-001 to STK-007."""
# # from datetime import datetime
# # from sqlalchemy import (
# #     Boolean, Column, CheckConstraint, DateTime, ForeignKey,
# #     Integer, Numeric, String, Text, Index
# # )
# # from sqlalchemy.orm import relationship
# # from app.core.database import Base
# # from app.core.enums import StockCategory, StockStatus, StockMovementType, ReservationStatus


# # class Product(Base):
# #     __tablename__ = "products"

# #     id           = Column(Integer, primary_key=True)
# #     company_id   = Column(Integer, ForeignKey("companies.id"), nullable=False)
# #     sku          = Column(String(100), nullable=True)
# #     name         = Column(String(300), nullable=False)
# #     description  = Column(Text, nullable=True)
# #     category     = Column(String(50), nullable=False, default=StockCategory.electronics)
# #     brand        = Column(String(100), nullable=True)
# #     unit         = Column(String(20), default="piece")
# #     cost_price   = Column(Numeric(14, 2), nullable=True)
# #     sell_price   = Column(Numeric(14, 2), nullable=True)
# #     is_active    = Column(Boolean, default=True)
# #     image_url    = Column(String(500), nullable=True)
# #     created_by   = Column(Integer, nullable=True)
# #     created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
# #     updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# #     deleted_at   = Column(DateTime, nullable=True)

# #     stock_items  = relationship("StockItem", back_populates="product", lazy="select")
# #     __table_args__ = (Index("ix_product_company", "company_id"),)


# # class Warehouse(Base):
# #     __tablename__ = "warehouses"

# #     id         = Column(Integer, primary_key=True)
# #     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
# #     branch_id  = Column(Integer, ForeignKey("branches.id"), nullable=True)
# #     name       = Column(String(200), nullable=False)
# #     address    = Column(Text, nullable=True)
# #     is_active  = Column(Boolean, default=True)
# #     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# #     deleted_at = Column(DateTime, nullable=True)

# #     stock_items = relationship("StockItem", back_populates="warehouse", lazy="select")


# # class StockItem(Base):
# #     __tablename__ = "stock_items"

# #     id           = Column(Integer, primary_key=True)
# #     product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
# #     warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
# #     quantity     = Column(Integer, default=0, nullable=False)
# #     reserved_qty = Column(Integer, default=0, nullable=False)
# #     min_quantity = Column(Integer, default=5, nullable=False)   # STK-004 alert threshold
# #     status       = Column(String(30), default=StockStatus.in_stock)
# #     updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# #     # STK-001: quantity >= 0 enforced at DB level
# #     __table_args__ = (
# #         CheckConstraint("quantity >= 0", name="chk_stock_non_negative"),
# #         CheckConstraint("reserved_qty >= 0", name="chk_reserved_non_negative"),
# #     )

# #     product   = relationship("Product", back_populates="stock_items")
# #     warehouse = relationship("Warehouse", back_populates="stock_items")

# #     @property
# #     def available_qty(self) -> int:
# #         return self.quantity - self.reserved_qty


# # class StockMovement(Base):
# #     """STK-002: every movement requires a reason and staff member."""
# #     __tablename__ = "stock_movements"

# #     id           = Column(Integer, primary_key=True)
# #     stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
# #     movement_type = Column(String(50), nullable=False)
# #     quantity     = Column(Integer, nullable=False)
# #     reason       = Column(Text, nullable=False)   # NOT NULL — STK-002
# #     reference_id = Column(Integer, nullable=True)  # order_id, shipment_id, etc.
# #     created_by   = Column(Integer, nullable=False)  # NOT NULL — STK-002
# #     created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


# # class Reservation(Base):
# #     """STK-005: expires 24h after creation if unpaid. STK-006: paid reservations protected."""
# #     __tablename__ = "reservations"

# #     id           = Column(Integer, primary_key=True)
# #     stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
# #     order_id     = Column(Integer, nullable=True)
# #     customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=False)
# #     quantity     = Column(Integer, nullable=False)
# #     status       = Column(String(30), default=ReservationStatus.active)
# #     expires_at   = Column(DateTime, nullable=False)  # created_at + 24h
# #     paid_at      = Column(DateTime, nullable=True)   # STK-006: set when paid
# #     created_by   = Column(Integer, nullable=True)
# #     created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
# #     updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# """TEHTEK — Stock Module Models. Rules: STK-001 to STK-007.
# v2: Added product catalog fields (name_fr, subcategory, barcode, model_number,
#     weight_kg, reorder_level, tax_rate, warranty_months, min_order_qty, tags).
# """
# from datetime import datetime
# from sqlalchemy import (
#     Boolean, Column, CheckConstraint, DateTime, ForeignKey,
#     Integer, Numeric, String, Text, Index, UniqueConstraint,
# )
# from sqlalchemy.orm import relationship
# from app.core.database import Base
# from app.core.enums import StockCategory, StockStatus, StockMovementType, ReservationStatus


# class Product(Base):
#     __tablename__ = "products"

#     id              = Column(Integer, primary_key=True)
#     company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)

#     # ── Identity ─────────────────────────────────────────────────────────────
#     sku             = Column(String(100), nullable=True)          # auto-generated if blank
#     barcode         = Column(String(100), nullable=True)          # EAN-13 / UPC / QR
#     model_number    = Column(String(100), nullable=True)          # manufacturer model ref

#     # ── Names ────────────────────────────────────────────────────────────────
#     name            = Column(String(300), nullable=False)
#     name_fr         = Column(String(300), nullable=True)          # French name (Cameroon)
#     description     = Column(Text, nullable=True)
#     brand           = Column(String(100), nullable=True)

#     # ── Classification ────────────────────────────────────────────────────────
#     category        = Column(String(50), nullable=False, default=StockCategory.electronics)
#     subcategory     = Column(String(100), nullable=True)
#     tags            = Column(Text, nullable=True)                 # comma-separated

#     # ── Units & Physical ─────────────────────────────────────────────────────
#     unit            = Column(String(20), default="pcs")
#     weight_kg       = Column(Numeric(8, 3), nullable=True)        # for shipping calc

#     # ── Pricing ───────────────────────────────────────────────────────────────
#     cost_price      = Column(Numeric(14, 2), nullable=True)
#     sell_price      = Column(Numeric(14, 2), nullable=True)
#     tax_rate        = Column(Numeric(5, 2), default=19.25)        # TVA default 19.25%

#     # ── Stock control ─────────────────────────────────────────────────────────
#     reorder_level   = Column(Integer, default=5)                  # alert threshold
#     min_order_qty   = Column(Integer, default=1)                  # min qty per order
#     warranty_months = Column(Integer, nullable=True)              # 0 = no warranty

#     # ── Status ────────────────────────────────────────────────────────────────
#     is_active       = Column(Boolean, default=True)
#     image_url       = Column(String(500), nullable=True)

#     # ── Audit ─────────────────────────────────────────────────────────────────
#     created_by      = Column(Integer, nullable=True)
#     created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#     deleted_at      = Column(DateTime, nullable=True)

#     stock_items = relationship("StockItem", back_populates="product", lazy="select")

#     __table_args__ = (
#         Index("ix_product_company", "company_id"),
#         Index("ix_product_subcategory", "company_id", "category", "subcategory"),
#     )


# class Warehouse(Base):
#     __tablename__ = "warehouses"

#     id         = Column(Integer, primary_key=True)
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
#     branch_id  = Column(Integer, ForeignKey("branches.id"), nullable=True)
#     name       = Column(String(200), nullable=False)
#     address    = Column(Text, nullable=True)
#     is_active  = Column(Boolean, default=True)
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     deleted_at = Column(DateTime, nullable=True)

#     stock_items = relationship("StockItem", back_populates="warehouse", lazy="select")


# class StockItem(Base):
#     __tablename__ = "stock_items"

#     id           = Column(Integer, primary_key=True)
#     product_id   = Column(Integer, ForeignKey("products.id"), nullable=False)
#     warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
#     quantity     = Column(Integer, default=0, nullable=False)
#     reserved_qty = Column(Integer, default=0, nullable=False)
#     min_quantity = Column(Integer, default=5, nullable=False)
#     status       = Column(String(30), default=StockStatus.in_stock)
#     updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     __table_args__ = (
#         CheckConstraint("quantity >= 0",     name="chk_stock_non_negative"),
#         CheckConstraint("reserved_qty >= 0", name="chk_reserved_non_negative"),
#     )

#     product   = relationship("Product",   back_populates="stock_items")
#     warehouse = relationship("Warehouse", back_populates="stock_items")

#     @property
#     def available_qty(self) -> int:
#         return self.quantity - self.reserved_qty


# class StockMovement(Base):
#     """STK-002: every movement requires a reason and staff member."""
#     __tablename__ = "stock_movements"

#     id            = Column(Integer, primary_key=True)
#     stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
#     movement_type = Column(String(50), nullable=False)
#     quantity      = Column(Integer, nullable=False)
#     reason        = Column(Text, nullable=False)
#     reference_id  = Column(Integer, nullable=True)
#     created_by    = Column(Integer, nullable=False)
#     created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)


# class Reservation(Base):
#     """STK-005: expires 24h after creation if unpaid. STK-006: paid reservations protected."""
#     __tablename__ = "reservations"

#     id            = Column(Integer, primary_key=True)
#     stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
#     order_id      = Column(Integer, nullable=True)
#     customer_id   = Column(Integer, ForeignKey("customers.id"), nullable=False)
#     quantity      = Column(Integer, nullable=False)
#     status        = Column(String(30), default=ReservationStatus.active)
#     expires_at    = Column(DateTime, nullable=False)
#     paid_at       = Column(DateTime, nullable=True)
#     created_by    = Column(Integer, nullable=True)
#     created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

"""TEHTEK — Stock Router v3.
Changes from v2:
  - SKU auto-generation: [CAT]-[BRAND3]-[SEQ4] e.g. ELE-HP-0001
  - Full product catalog fields (name_fr, subcategory, barcode, model_number,
    weight_kg, tax_rate, warranty_months, min_order_qty, tags)
  - reorder_level now lives on Product (authoritative) + synced to StockItem
  - Subcategory validation
  - ACC-007: auth at router level
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.stock.models import Product, Warehouse, StockItem, StockMovement, Reservation
from app.core.enums import ReservationStatus, StockStatus

router = APIRouter(
    prefix="/api/v1",
    tags=["stock"],
    dependencies=[Depends(get_current_user)],
)

# ─── Category / subcategory taxonomy ─────────────────────────────────────────

CAT_PREFIX: dict[str, str] = {
    "electronics":    "ELE",
    "solar":          "SOL",
    "security":       "SEC",
    "networking":     "NET",
    "cables":         "CAB",
    "accessories":    "ACC",
    "consumables":    "CON",
    "cargo_supplies": "CGO",
    "other":          "OTH",
}

SUBCATEGORIES: dict[str, list[str]] = {
    "electronics":    ["laptop", "desktop", "smartphone", "tablet", "printer",
                       "tv_display", "camera", "audio", "gaming", "component", "other"],
    "solar":          ["panel", "battery", "inverter", "charge_controller",
                       "mounting", "cable", "other"],
    "security":       ["ip_camera", "nvr_dvr", "access_control", "alarm",
                       "sensor", "cable", "other"],
    "networking":     ["router", "switch", "access_point", "sfp_module",
                       "firewall", "cable", "other"],
    "cables":         ["hdmi", "usb", "ethernet", "power", "fiber",
                       "coaxial", "display_port", "other"],
    "accessories":    ["bag", "case", "mouse", "keyboard", "monitor_stand",
                       "hub", "adapter", "other"],
    "consumables":    ["ink_cartridge", "toner", "paper", "battery_aa",
                       "cleaning_kit", "other"],
    "cargo_supplies": ["box", "tape", "bubble_wrap", "label", "pallet",
                       "strap", "other"],
    "other":          ["other"],
}

UNITS = ["pcs", "kg", "g", "m", "cm", "l", "ml", "box", "set", "pair", "roll", "sheet"]


# ─── SKU auto-generation ──────────────────────────────────────────────────────

def _generate_sku(
    db: Session, category: str, brand: Optional[str], company_id: int
) -> str:
    """
    Format: [CAT3]-[BRAND3]-[SEQ4]  e.g. ELE-HP-0001
            [CAT3]-[SEQ4]           e.g. SOL-0003 (no brand)
    Sequence is per category+brand prefix, per company.
    """
    cat_code = CAT_PREFIX.get(category, "OTH")
    if brand and brand.strip():
        brand_code = brand.strip()[:3].upper()
        prefix = f"{cat_code}-{brand_code}-"
    else:
        prefix = f"{cat_code}-"

    count = (
        db.query(func.count(Product.id))
        .filter(
            Product.company_id == company_id,
            Product.sku.like(f"{prefix}%"),
            Product.deleted_at.is_(None),
        )
        .scalar()
    ) or 0

    candidate = f"{prefix}{(count + 1):04d}"

    # Collision guard (in case of deletions creating gaps)
    while db.query(Product).filter_by(sku=candidate, company_id=company_id).first():
        count += 1
        candidate = f"{prefix}{(count + 1):04d}"

    return candidate


# ─── Serializers ──────────────────────────────────────────────────────────────

def _product_out(p: Product) -> dict:
    return {
        "id":              p.id,
        "company_id":      p.company_id,
        # Identity
        "sku":             p.sku,
        "barcode":         p.barcode,
        "model_number":    p.model_number,
        # Names
        "name":            p.name,
        "name_fr":         p.name_fr,
        "description":     p.description,
        "brand":           p.brand,
        # Classification
        "category":        p.category,
        "subcategory":     p.subcategory,
        "tags":            p.tags,
        # Units & Physical
        "unit":            p.unit,
        "weight_kg":       float(p.weight_kg)     if p.weight_kg     else None,
        # Pricing
        "cost_price":      float(p.cost_price)    if p.cost_price    else None,
        "selling_price":   float(p.sell_price)    if p.sell_price    else None,
        "tax_rate":        float(p.tax_rate)       if p.tax_rate      else 19.25,
        # Stock control
        "reorder_level":   p.reorder_level        if p.reorder_level is not None else 5,
        "min_order_qty":   p.min_order_qty        if p.min_order_qty is not None else 1,
        "warranty_months": p.warranty_months,
        # Status
        "is_active":       p.is_active,
        "image_url":       p.image_url,
        # Audit
        "created_at":      p.created_at.isoformat() if p.created_at else None,
        "updated_at":      p.updated_at.isoformat() if p.updated_at else None,
    }


def _stock_item_out(item: StockItem) -> dict:
    return {
        "id":           item.id,
        "product_id":   item.product_id,
        "warehouse_id": item.warehouse_id,
        "quantity":     item.quantity,
        "reserved":     item.reserved_qty,
        "available":    item.available_qty,
        "min_quantity": item.min_quantity,
        "status":       item.status,
    }


def _movement_out(mv: StockMovement, product_id: int) -> dict:
    return {
        "id":             mv.id,
        "product_id":     product_id,
        "stock_item_id":  mv.stock_item_id,
        "movement_type":  mv.movement_type,
        "quantity":       mv.quantity,
        "reason":         mv.reason,
        "created_at":     mv.created_at.isoformat() if mv.created_at else None,
    }


# ─── Helper: get or create StockItem ─────────────────────────────────────────

def _get_or_create_stock_item(
    db: Session, product: Product, company_id: int
) -> StockItem:
    item = db.query(StockItem).filter_by(product_id=product.id).first()
    if item:
        return item

    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.company_id == company_id,
            Warehouse.is_active.is_(True),
            Warehouse.deleted_at.is_(None),
        )
        .first()
    )
    if not warehouse:
        warehouse = Warehouse(
            company_id=company_id,
            name="Entrepôt principal",
            is_active=True,
        )
        db.add(warehouse)
        db.flush()

    item = StockItem(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=0,
        reserved_qty=0,
        min_quantity=product.reorder_level or 5,
        status=StockStatus.out_of_stock,
    )
    db.add(item)
    db.flush()
    return item


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    # Required
    name:            str
    category:        str
    # Optional identity
    sku:             Optional[str]   = None   # auto-generated if omitted
    barcode:         Optional[str]   = None
    model_number:    Optional[str]   = None
    # Names
    name_fr:         Optional[str]   = None
    description:     Optional[str]   = None
    brand:           Optional[str]   = None
    # Classification
    subcategory:     Optional[str]   = None
    tags:            Optional[str]   = None
    # Physical
    unit:            str             = "pcs"
    weight_kg:       Optional[float] = None
    # Pricing
    cost_price:      Optional[float] = None
    selling_price:   Optional[float] = None
    tax_rate:        float           = 19.25
    # Stock control
    reorder_level:   int             = 5
    min_order_qty:   int             = 1
    warranty_months: Optional[int]   = None
    # Status
    is_active:       bool            = True


class ProductUpdate(BaseModel):
    name:            Optional[str]   = None
    name_fr:         Optional[str]   = None
    brand:           Optional[str]   = None
    category:        Optional[str]   = None
    subcategory:     Optional[str]   = None
    tags:            Optional[str]   = None
    unit:            Optional[str]   = None
    weight_kg:       Optional[float] = None
    barcode:         Optional[str]   = None
    model_number:    Optional[str]   = None
    description:     Optional[str]   = None
    cost_price:      Optional[float] = None
    selling_price:   Optional[float] = None
    tax_rate:        Optional[float] = None
    reorder_level:   Optional[int]   = None
    min_order_qty:   Optional[int]   = None
    warranty_months: Optional[int]   = None
    is_active:       Optional[bool]  = None


class StockMovementCreate(BaseModel):
    product_id:    int
    movement_type: str              # "in" | "out" | "adjustment"
    quantity:      float
    reason:        Optional[str] = None


class StockAdjust(BaseModel):
    quantity: int
    reason:   str


class ReservationCreate(BaseModel):
    customer_id: int
    quantity:    int
    order_id:    Optional[int] = None


# ─── Utility endpoint: taxonomy ───────────────────────────────────────────────

@router.get("/products/taxonomy")
def get_taxonomy(_=Depends(get_current_user)):
    """Return categories, subcategories, and units for frontend dropdowns."""
    return {
        "categories":    list(CAT_PREFIX.keys()),
        "subcategories": SUBCATEGORIES,
        "units":         UNITS,
        "cat_prefix":    CAT_PREFIX,
    }


# ─── Products ─────────────────────────────────────────────────────────────────

@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    # Validate subcategory if provided
    if body.subcategory:
        valid = SUBCATEGORIES.get(body.category, [])
        if body.subcategory not in valid:
            raise HTTPException(
                400,
                f"Invalid subcategory '{body.subcategory}' for category '{body.category}'. "
                f"Valid: {valid}",
            )

    # Validate barcode uniqueness
    if body.barcode:
        clash = db.query(Product).filter(
            Product.company_id == current_user.company_id,
            Product.barcode == body.barcode,
            Product.deleted_at.is_(None),
        ).first()
        if clash:
            raise HTTPException(409, f"Barcode '{body.barcode}' already used by {clash.name}")

    # Auto-generate SKU if not provided
    sku = body.sku.strip() if body.sku and body.sku.strip() else None
    if not sku:
        sku = _generate_sku(db, body.category, body.brand, current_user.company_id)

    p = Product(
        company_id=current_user.company_id,
        created_by=current_user.id,
        sku=sku,
        barcode=body.barcode,
        model_number=body.model_number,
        name=body.name,
        name_fr=body.name_fr,
        description=body.description,
        brand=body.brand,
        category=body.category,
        subcategory=body.subcategory,
        tags=body.tags,
        unit=body.unit,
        weight_kg=body.weight_kg,
        cost_price=body.cost_price,
        sell_price=body.selling_price,
        tax_rate=body.tax_rate,
        reorder_level=body.reorder_level,
        min_order_qty=body.min_order_qty,
        warranty_months=body.warranty_months,
        is_active=body.is_active,
    )
    db.add(p)
    db.flush()

    # Auto-create StockItem so product appears immediately
    _get_or_create_stock_item(db, p, current_user.company_id)

    db.commit()
    db.refresh(p)
    return _product_out(p)


@router.get("/products")
def list_products(
    category:    Optional[str] = None,
    subcategory: Optional[str] = None,
    is_active:   Optional[bool] = None,
    limit:       int = 200,
    skip:        int = 0,
    db:          Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    q = db.query(Product).filter(
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    )
    if category:    q = q.filter(Product.category == category)
    if subcategory: q = q.filter(Product.subcategory == subcategory)
    if is_active is not None: q = q.filter(Product.is_active == is_active)

    products = q.order_by(Product.name).offset(skip).limit(limit).all()
    return [_product_out(p) for p in products]


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("stock:read")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    ).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_out(p)


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    body:       ProductUpdate,
    db:         Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    ).first()
    if not p:
        raise HTTPException(404, "Product not found")

    # Validate subcategory if changing category
    cat = body.category or p.category
    if body.subcategory:
        valid = SUBCATEGORIES.get(cat, [])
        if body.subcategory not in valid:
            raise HTTPException(400, f"Invalid subcategory '{body.subcategory}' for '{cat}'")

    # Barcode uniqueness
    if body.barcode and body.barcode != p.barcode:
        clash = db.query(Product).filter(
            Product.company_id == p.company_id,
            Product.barcode == body.barcode,
            Product.id != p.id,
            Product.deleted_at.is_(None),
        ).first()
        if clash:
            raise HTTPException(409, f"Barcode already used by {clash.name}")

    # Apply updates
    fields = {
        "name": "name", "name_fr": "name_fr", "brand": "brand",
        "category": "category", "subcategory": "subcategory", "tags": "tags",
        "unit": "unit", "description": "description", "barcode": "barcode",
        "model_number": "model_number", "weight_kg": "weight_kg",
        "cost_price": "cost_price", "tax_rate": "tax_rate",
        "reorder_level": "reorder_level", "min_order_qty": "min_order_qty",
        "warranty_months": "warranty_months", "is_active": "is_active",
    }
    for schema_field, model_field in fields.items():
        val = getattr(body, schema_field)
        if val is not None:
            setattr(p, model_field, val)

    if body.selling_price is not None:
        p.sell_price = body.selling_price

    # Sync reorder_level to StockItem
    if body.reorder_level is not None:
        item = db.query(StockItem).filter_by(product_id=p.id).first()
        if item:
            item.min_quantity = body.reorder_level

    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return _product_out(p)


# ─── Stock Items ──────────────────────────────────────────────────────────────

@router.get("/stock-items")
def list_stock_items(
    limit: int = 200,
    db:    Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    items = (
        db.query(StockItem)
        .join(Product, StockItem.product_id == Product.id)
        .filter(
            Product.company_id == current_user.company_id,
            Product.deleted_at.is_(None),
        )
        .limit(limit)
        .all()
    )
    return [_stock_item_out(i) for i in items]


# ─── Stock Movements ──────────────────────────────────────────────────────────

@router.get("/stock-movements")
def list_stock_movements(
    product_id: Optional[int] = None,
    limit:      int = 100,
    db:         Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    q = (
        db.query(StockMovement, StockItem)
        .join(StockItem, StockMovement.stock_item_id == StockItem.id)
        .join(Product,   StockItem.product_id == Product.id)
        .filter(
            Product.company_id == current_user.company_id,
            Product.deleted_at.is_(None),
        )
    )
    if product_id:
        q = q.filter(StockItem.product_id == product_id)

    rows = q.order_by(StockMovement.created_at.desc()).limit(limit).all()
    return [_movement_out(mv, item.product_id) for mv, item in rows]


@router.post("/stock-movements", status_code=201)
def create_stock_movement(
    body: StockMovementCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    """STK-001: qty >= 0. STK-002: reason + created_by required."""
    if not body.reason or not body.reason.strip():
        raise HTTPException(400, "A reason is required for stock movements (STK-002)")

    qty = int(body.quantity)
    if qty <= 0:
        raise HTTPException(400, "Quantity must be > 0")

    if body.movement_type not in ("in", "out", "adjustment"):
        raise HTTPException(400, "movement_type: in | out | adjustment")

    product = db.query(Product).filter(
        Product.id == body.product_id,
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")

    item = _get_or_create_stock_item(db, product, current_user.company_id)

    if body.movement_type == "out":
        if item.quantity - qty < 0:
            raise HTTPException(
                400,
                f"Insufficient stock. Available: {item.available_qty}, "
                f"requested: {qty} (STK-001)",
            )
        item.quantity -= qty
    else:
        item.quantity += qty

    # Sync reorder_level from Product
    item.min_quantity = product.reorder_level or 5

    if item.quantity == 0:
        item.status = StockStatus.out_of_stock
    elif item.quantity < item.min_quantity:
        item.status = StockStatus.low_stock
    else:
        item.status = StockStatus.in_stock

    mv = StockMovement(
        stock_item_id=item.id,
        movement_type=body.movement_type,
        quantity=qty,
        reason=body.reason.strip(),
        created_by=current_user.id,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return _movement_out(mv, product.id)


# ─── Existing endpoints (unchanged) ──────────────────────────────────────────

@router.post("/stock-items/{stock_item_id}/adjust")
def adjust_stock(
    stock_item_id: int, body: StockAdjust,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:adjust")),
):
    item = db.query(StockItem).filter_by(id=stock_item_id).first()
    if not item:
        raise HTTPException(404, "Stock item not found")
    new_qty = item.quantity + body.quantity
    if new_qty < 0:
        raise HTTPException(400, "Stock cannot go below zero (STK-001)")
    item.quantity = new_qty
    item.status = (
        StockStatus.out_of_stock if new_qty == 0 else
        StockStatus.low_stock    if new_qty < item.min_quantity else
        StockStatus.in_stock
    )
    db.add(StockMovement(
        stock_item_id=item.id,
        movement_type="adjustment_add" if body.quantity > 0 else "adjustment_remove",
        quantity=abs(body.quantity),
        reason=body.reason,
        created_by=current_user.id,
    ))
    db.commit()
    return _stock_item_out(item)


@router.post("/stock-items/{stock_item_id}/reserve", status_code=201)
def create_reservation(
    stock_item_id: int, body: ReservationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = db.query(StockItem).filter_by(id=stock_item_id).first()
    if not item:
        raise HTTPException(404, "Stock item not found")
    if item.available_qty < body.quantity:
        raise HTTPException(400, f"Only {item.available_qty} units available")
    item.reserved_qty += body.quantity
    reservation = Reservation(
        stock_item_id=stock_item_id,
        customer_id=body.customer_id,
        quantity=body.quantity,
        order_id=body.order_id,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        created_by=current_user.id,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation