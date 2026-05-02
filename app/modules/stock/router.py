"""TEHTEK — Stock Router. ACC-007: auth at router level.
Patch v2 — adds missing endpoints + fixes field name mismatches.

Mismatches fixed:
  sell_price      → returned as selling_price (frontend contract)
  name_fr         → not in DB, returned as null
  reorder_level   → mapped from StockItem.min_quantity
  reserved_qty    → returned as reserved
  available_qty   → returned as available
  stock_item_id   → resolved from product_id in POST /stock-movements
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.stock.models import Product, Warehouse, StockItem, StockMovement, Reservation
from app.core.enums import ReservationStatus, StockStatus, StockMovementType

router = APIRouter(
    prefix="/api/v1",
    tags=["stock"],
    dependencies=[Depends(get_current_user)],
)


# ─── Serializers (field name translation) ────────────────────────────────────

def _product_out(p: Product, reorder_level: int = 5) -> dict:
    """Return product dict with frontend-compatible field names."""
    return {
        "id":            p.id,
        "sku":           p.sku,
        "name":          p.name,
        "name_fr":       None,              # column does not exist in DB
        "description":   p.description,
        "category":      p.category,
        "brand":         p.brand,
        "unit":          p.unit,
        "cost_price":    float(p.cost_price)   if p.cost_price   else None,
        "selling_price": float(p.sell_price)   if p.sell_price   else None,
        "reorder_level": reorder_level,         # from StockItem.min_quantity
        "is_active":     p.is_active,
        "created_at":    p.created_at.isoformat() if p.created_at else None,
    }


def _stock_item_out(item: StockItem) -> dict:
    """Return stock item dict with frontend-compatible field names."""
    return {
        "id":           item.id,
        "product_id":   item.product_id,
        "warehouse_id": item.warehouse_id,
        "quantity":     item.quantity,
        "reserved":     item.reserved_qty,      # frontend: reserved
        "available":    item.available_qty,     # frontend: available
        "min_quantity": item.min_quantity,
        "status":       item.status,
    }


def _movement_out(mv: StockMovement, product_id: int) -> dict:
    """Return movement dict with product_id instead of stock_item_id."""
    return {
        "id":            mv.id,
        "product_id":    product_id,            # frontend needs this
        "stock_item_id": mv.stock_item_id,
        "movement_type": mv.movement_type,
        "quantity":      mv.quantity,
        "reason":        mv.reason,
        "created_at":    mv.created_at.isoformat() if mv.created_at else None,
    }


# ─── Helper: get or create StockItem for a product ───────────────────────────

def _get_or_create_stock_item(
    db: Session, product: Product, company_id: int
) -> StockItem:
    """
    Find existing StockItem for product, or create one using the first
    active warehouse for the company. Auto-creates a default warehouse
    if none exists (first-run scenario).
    """
    item = (
        db.query(StockItem)
        .filter(StockItem.product_id == product.id)
        .first()
    )
    if item:
        return item

    # Find first warehouse for this company
    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.company_id == company_id,
            Warehouse.is_active.is_(True),
            Warehouse.deleted_at.is_(None),
        )
        .first()
    )

    # Auto-create default warehouse if none exists
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
        min_quantity=5,
        status=StockStatus.out_of_stock,
    )
    db.add(item)
    db.flush()
    return item


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name:          str
    category:      str
    unit:          str = "piece"
    sku:           Optional[str]   = None
    brand:         Optional[str]   = None
    description:   Optional[str]  = None
    cost_price:    Optional[float] = None
    selling_price: Optional[float] = None   # mapped → sell_price in DB
    # name_fr and reorder_level sent by frontend — accepted, name_fr ignored,
    # reorder_level stored on the auto-created StockItem
    name_fr:       Optional[str]   = None   # no DB column — accepted, ignored
    reorder_level: Optional[int]   = 5      # stored on StockItem.min_quantity
    is_active:     Optional[bool]  = True


class ProductUpdate(BaseModel):
    name:          Optional[str]   = None
    category:      Optional[str]   = None
    unit:          Optional[str]   = None
    brand:         Optional[str]   = None
    description:   Optional[str]  = None
    cost_price:    Optional[float] = None
    selling_price: Optional[float] = None
    reorder_level: Optional[int]   = None
    is_active:     Optional[bool]  = None


class StockMovementCreate(BaseModel):
    product_id:    int
    movement_type: str              # "in" | "out" | "adjustment"
    quantity:      float
    reason:        Optional[str] = None


class StockAdjust(BaseModel):
    quantity: int
    reason:   str                   # STK-002: mandatory


class ReservationCreate(BaseModel):
    customer_id: int
    quantity:    int
    order_id:    Optional[int] = None


# ─── Products ─────────────────────────────────────────────────────────────────

@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    p = Product(
        company_id=current_user.company_id,
        created_by=current_user.id,
        name=body.name,
        category=body.category,
        unit=body.unit,
        sku=body.sku,
        brand=body.brand,
        description=body.description,
        cost_price=body.cost_price,
        sell_price=body.selling_price,      # field rename
        is_active=body.is_active if body.is_active is not None else True,
    )
    db.add(p)
    db.flush()

    # Auto-create StockItem so product appears in stock list immediately
    item = _get_or_create_stock_item(db, p, current_user.company_id)

    # Apply reorder_level to StockItem
    if body.reorder_level is not None:
        item.min_quantity = body.reorder_level

    db.commit()
    db.refresh(p)
    return _product_out(p, reorder_level=item.min_quantity)


@router.get("/products")
def list_products(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    products = (
        db.query(Product)
        .filter(
            Product.company_id == current_user.company_id,
            Product.deleted_at.is_(None),
        )
        .limit(limit)
        .all()
    )

    # Build lookup: product_id → min_quantity from StockItem
    product_ids = [p.id for p in products]
    stock_items = (
        db.query(StockItem)
        .filter(StockItem.product_id.in_(product_ids))
        .all()
    ) if product_ids else []
    reorder_map = {si.product_id: si.min_quantity for si in stock_items}

    return [_product_out(p, reorder_map.get(p.id, 5)) for p in products]


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    ).first()
    if not p:
        raise HTTPException(404, "Product not found")

    item = db.query(StockItem).filter_by(product_id=p.id).first()
    return _product_out(p, reorder_level=item.min_quantity if item else 5)


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    ).first()
    if not p:
        raise HTTPException(404, "Product not found")

    if body.name          is not None: p.name        = body.name
    if body.category      is not None: p.category    = body.category
    if body.unit          is not None: p.unit         = body.unit
    if body.brand         is not None: p.brand        = body.brand
    if body.description   is not None: p.description  = body.description
    if body.cost_price    is not None: p.cost_price   = body.cost_price
    if body.selling_price is not None: p.sell_price   = body.selling_price
    if body.is_active     is not None: p.is_active    = body.is_active
    p.updated_at = datetime.utcnow()

    # Update reorder_level on StockItem
    item = db.query(StockItem).filter_by(product_id=p.id).first()
    if item and body.reorder_level is not None:
        item.min_quantity = body.reorder_level

    db.commit()
    db.refresh(p)
    return _product_out(p, reorder_level=item.min_quantity if item else 5)


# ─── Stock Items ──────────────────────────────────────────────────────────────

@router.get("/stock-items")
def list_stock_items(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    """
    List all stock items for the company.
    Joins through products to scope by company_id.
    Returns frontend-compatible field names (available, reserved).
    """
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
    return [_stock_item_out(item) for item in items]


# ─── Stock Movements ──────────────────────────────────────────────────────────

@router.get("/stock-movements")
def list_stock_movements(
    product_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    """
    List stock movements for this company.
    Returns product_id (resolved from stock_item → product).
    """
    q = (
        db.query(StockMovement, StockItem)
        .join(StockItem, StockMovement.stock_item_id == StockItem.id)
        .join(Product, StockItem.product_id == Product.id)
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
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    """
    Create a stock movement from a product_id.
    Resolves product → stock_item (auto-creates if needed).
    Enforces STK-001 (quantity >= 0) and STK-002 (reason required).

    movement_type:
      in          → add quantity
      out         → subtract quantity (STK-001: blocked if goes below 0)
      adjustment  → add quantity (manual correction)
    """
    # STK-002: reason required
    if not body.reason or not body.reason.strip():
        raise HTTPException(400, "A reason is required for all stock movements (STK-002)")

    qty = int(body.quantity)
    if qty <= 0:
        raise HTTPException(400, "Quantity must be greater than zero")

    if body.movement_type not in ("in", "out", "adjustment"):
        raise HTTPException(400, "movement_type must be: in | out | adjustment")

    # Resolve product
    product = db.query(Product).filter(
        Product.id == body.product_id,
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")

    # Get or create StockItem
    item = _get_or_create_stock_item(db, product, current_user.company_id)

    # Apply movement — STK-001: quantity >= 0
    if body.movement_type == "out":
        if item.quantity - qty < 0:
            raise HTTPException(
                400,
                f"Insufficient stock. Available: {item.available_qty}, requested: {qty} (STK-001)"
            )
        item.quantity -= qty
    else:
        # "in" and "adjustment" both add to stock
        item.quantity += qty

    # Update stock status
    if item.quantity == 0:
        item.status = StockStatus.out_of_stock
    elif item.quantity < item.min_quantity:
        item.status = StockStatus.low_stock
    else:
        item.status = StockStatus.in_stock

    # Record movement — STK-002: reason + created_by mandatory
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


# ─── Stock adjustment (existing endpoint — kept unchanged) ────────────────────

@router.post("/stock-items/{stock_item_id}/adjust")
def adjust_stock(
    stock_item_id: int, body: StockAdjust,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:adjust")),
):
    """STK-001: quantity cannot go below 0. STK-002: reason required."""
    item = db.query(StockItem).filter_by(id=stock_item_id).first()
    if not item:
        raise HTTPException(404, "Stock item not found")
    new_qty = item.quantity + body.quantity
    if new_qty < 0:
        raise HTTPException(400, "Stock cannot go below zero (STK-001)")
    item.quantity = new_qty
    item.status = StockStatus.out_of_stock if new_qty == 0 else (
        StockStatus.low_stock if new_qty < item.min_quantity else StockStatus.in_stock
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


# ─── Reservations (existing endpoint — kept unchanged) ────────────────────────

@router.post("/stock-items/{stock_item_id}/reserve", status_code=201)
def create_reservation(
    stock_item_id: int, body: ReservationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """STK-005: expires in 24h."""
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