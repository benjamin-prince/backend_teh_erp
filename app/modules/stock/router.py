"""TEHTEK — Stock Router. ACC-007: auth at router level."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
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


class ProductCreate(BaseModel):
    name: str
    category: str
    brand: Optional[str] = None
    unit: str = "piece"
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    sku: Optional[str] = None
    description: Optional[str] = None

class StockAdjust(BaseModel):
    quantity: int
    reason: str   # STK-002: mandatory

class ReservationCreate(BaseModel):
    customer_id: int
    quantity: int
    order_id: Optional[int] = None


# ── Products ──────────────────────────────────────────────────────────────────

@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    p = Product(**body.model_dump(), company_id=current_user.company_id, created_by=current_user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    return db.query(Product).filter(
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None)
    ).all()

@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), _=Depends(require_permission("stock:read"))):
    p = db.query(Product).filter_by(id=product_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return p

# ── Stock adjustments ─────────────────────────────────────────────────────────

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
    return item

# ── Reservations ──────────────────────────────────────────────────────────────

@router.post("/stock-items/{stock_item_id}/reserve", status_code=201)
def create_reservation(
    stock_item_id: int, body: ReservationCreate,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
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
