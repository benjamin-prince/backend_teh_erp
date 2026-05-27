import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.stock.models import Product, StockItem, StockMovement, Reservation
from app.modules.stock.schemas import (
    ProductCreate,
    ProductUpdate,
    ReservationCreate,
    StockAdjust,
    StockMovementCreate,
)
from app.modules.stock.service import (
    CAT_PREFIX,
    SUBCATEGORIES,
    UNITS,
    generate_sku,
    get_or_create_stock_item,
    movement_out,
    product_out,
    stock_item_out,
    update_stock_status,
    validate_subcategory,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["stock"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/products/taxonomy")
def get_taxonomy():
    return {
        "categories": list(CAT_PREFIX.keys()),
        "subcategories": SUBCATEGORIES,
        "units": UNITS,
        "cat_prefix": CAT_PREFIX,
    }


@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    validate_subcategory(body.category, body.subcategory)

    if body.barcode:
        clash = db.query(Product).filter(
            Product.company_id == current_user.company_id,
            Product.barcode == body.barcode,
            Product.deleted_at.is_(None),
        ).first()
        if clash:
            raise HTTPException(409, f"Barcode '{body.barcode}' already used by {clash.name}")

    sku = body.sku.strip() if body.sku and body.sku.strip() else None
    if not sku:
        sku = generate_sku(db, body.category, body.brand, current_user.company_id)

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
        condition=body.condition,
        is_active=body.is_active,
        is_published=body.is_published,
        is_featured=body.is_featured,
        compare_price=body.compare_price,
        image_url=body.image_url,
    )

    db.add(p)
    db.flush()

    item = get_or_create_stock_item(db, p, current_user.company_id)
    item.min_quantity = p.reorder_level or 5

    db.commit()
    db.refresh(p)
    return product_out(p)


@router.get("/products")
def list_products(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 200,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    q = db.query(Product).filter(
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    )

    if category:
        q = q.filter(Product.category == category)

    if subcategory:
        q = q.filter(Product.subcategory == subcategory)

    if is_active is not None:
        q = q.filter(Product.is_active == is_active)

    products = q.order_by(Product.name).offset(skip).limit(limit).all()
    return [product_out(p) for p in products]


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    ).first()

    if not p:
        raise HTTPException(404, "Product not found")

    return product_out(p)


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == current_user.company_id,
        Product.deleted_at.is_(None),
    ).first()

    if not p:
        raise HTTPException(404, "Product not found")

    category = body.category or p.category
    validate_subcategory(category, body.subcategory)

    if body.barcode and body.barcode != p.barcode:
        clash = db.query(Product).filter(
            Product.company_id == p.company_id,
            Product.barcode == body.barcode,
            Product.id != p.id,
            Product.deleted_at.is_(None),
        ).first()
        if clash:
            raise HTTPException(409, f"Barcode already used by {clash.name}")

    fields = {
        "name": "name",
        "name_fr": "name_fr",
        "brand": "brand",
        "category": "category",
        "subcategory": "subcategory",
        "tags": "tags",
        "unit": "unit",
        "description": "description",
        "barcode": "barcode",
        "model_number": "model_number",
        "weight_kg": "weight_kg",
        "cost_price": "cost_price",
        "tax_rate": "tax_rate",
        "reorder_level": "reorder_level",
        "min_order_qty": "min_order_qty",
        "warranty_months": "warranty_months",
        "condition": "condition",
        "is_active": "is_active",
        "is_published": "is_published",
        "is_featured": "is_featured",
        "compare_price": "compare_price",
        "image_url": "image_url",
    }

    for schema_field, model_field in fields.items():
        value = getattr(body, schema_field, None)
        if value is not None:
            setattr(p, model_field, value)
    # Booleans need explicit False check
    for bool_field in ("is_active", "is_published", "is_featured"):
        v = getattr(body, bool_field, None)
        if v is False:
            setattr(p, bool_field, False)

    if body.selling_price is not None:
        p.sell_price = body.selling_price

    if body.reorder_level is not None:
        item = db.query(StockItem).filter_by(product_id=p.id).first()
        if item:
            item.min_quantity = body.reorder_level
            update_stock_status(item)

    p.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(p)
    return product_out(p)


@router.get("/stock-items")
def list_stock_items(
    limit: int = 200,
    db: Session = Depends(get_db),
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

    return [stock_item_out(item) for item in items]


@router.get("/stock-movements")
def list_stock_movements(
    product_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:read")),
):
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
    return [movement_out(mv, item.product_id) for mv, item in rows]


@router.post("/stock-movements", status_code=201)
def create_stock_movement(
    body: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("stock:receive")),
):
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

    item = get_or_create_stock_item(db, product, current_user.company_id)

    if body.movement_type == "out":
        if item.quantity - qty < 0:
            raise HTTPException(
                400,
                f"Insufficient stock. Available: {item.available_qty}, requested: {qty} (STK-001)",
            )
        item.quantity -= qty
    else:
        item.quantity += qty

    item.min_quantity = product.reorder_level or 5
    update_stock_status(item)

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

    return movement_out(mv, product.id)


@router.post("/stock-items/{stock_item_id}/adjust")
def adjust_stock(
    stock_item_id: int,
    body: StockAdjust,
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
    update_stock_status(item)

    db.add(
        StockMovement(
            stock_item_id=item.id,
            movement_type="adjustment_add" if body.quantity > 0 else "adjustment_remove",
            quantity=abs(body.quantity),
            reason=body.reason,
            created_by=current_user.id,
        )
    )

    db.commit()
    return stock_item_out(item)


@router.post("/stock-items/{stock_item_id}/reserve", status_code=201)
def create_reservation(
    stock_item_id: int,
    body: ReservationCreate,
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


# ── Cloudinary signed upload (product images) ──────────────────────────────────

class CloudinarySignResponse(BaseModel):
    signature:  str
    timestamp:  int
    api_key:    str
    cloud_name: str
    folder:     str

@router.post("/uploads/cloudinary-signature", response_model=CloudinarySignResponse)
def product_image_upload_signature(
    current_user=Depends(get_current_user),
):
    """Return a short-lived signed payload for direct browser → Cloudinary upload (product images)."""
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
        raise HTTPException(503, "Cloudinary not configured")

    folder    = "tehtek/products"
    timestamp = int(time.time())
    to_sign   = f"folder={folder}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(to_sign.encode()).hexdigest()

    return CloudinarySignResponse(
        signature=signature,
        timestamp=timestamp,
        api_key=settings.CLOUDINARY_API_KEY,
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        folder=folder,
    )
