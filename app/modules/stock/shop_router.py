"""
Public shop API — no authentication required.
Used by tehtek.com to display products.

Endpoints:
  GET  /api/v1/shop/products          — paginated list of published products
  GET  /api/v1/shop/products/{id}     — single product detail
  GET  /api/v1/shop/categories        — list categories that have published products
  GET  /api/v1/shop/featured          — featured products (is_featured=True)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.stock.models import Product, StockItem

router = APIRouter(prefix="/api/v1/shop", tags=["shop-public"])


def _to_shop_out(product: Product, db: Session) -> dict:
    """Serialize a product for public consumption (no cost_price)."""
    # Sum available qty across all warehouses
    stock_row = (
        db.query(func.sum(StockItem.quantity - StockItem.reserved_qty))
        .filter(StockItem.product_id == product.id)
        .scalar()
    )
    available = max(int(stock_row or 0), 0)

    return {
        "id": product.id,
        "sku": product.sku or "",
        "name": product.name,
        "name_fr": product.name_fr,
        "description": product.description,
        "brand": product.brand,
        "category": product.category,
        "subcategory": product.subcategory,
        "model_number": product.model_number,
        "condition": product.condition or "new",
        "tags": product.tags,
        "weight_kg": float(product.weight_kg) if product.weight_kg is not None else None,
        "sell_price": float(product.sell_price) if product.sell_price is not None else None,
        "compare_price": float(product.compare_price) if product.compare_price is not None else None,
        "warranty_months": product.warranty_months,
        "image_url": product.image_url,
        "is_featured": bool(product.is_featured),
        "stock_available": available,
    }


@router.get("/products")
def list_shop_products(
    category: Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    featured: Optional[bool] = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List published products — no auth required."""
    q = (
        db.query(Product)
        .filter(
            Product.is_published == True,  # noqa: E712
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
    )
    if category:
        q = q.filter(Product.category == category)
    if featured is True:
        q = q.filter(Product.is_featured == True)  # noqa: E712
    if search:
        term = f"%{search}%"
        q = q.filter(
            Product.name.ilike(term)
            | Product.name_fr.ilike(term)
            | Product.brand.ilike(term)
            | Product.description.ilike(term)
        )

    total = q.count()
    products = (
        q.order_by(Product.is_featured.desc(), Product.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": [_to_shop_out(p, db) for p in products],
    }


@router.get("/products/{product_id}")
def get_shop_product(product_id: int, db: Session = Depends(get_db)):
    """Single product detail — no auth required."""
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_published == True,  # noqa: E712
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
        .first()
    )
    if not product:
        raise HTTPException(404, "Product not found")
    return _to_shop_out(product, db)


@router.get("/categories")
def list_shop_categories(db: Session = Depends(get_db)):
    """Categories that have at least one published product."""
    rows = (
        db.query(Product.category, func.count(Product.id).label("count"))
        .filter(
            Product.is_published == True,  # noqa: E712
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    return [{"category": r.category, "count": r.count} for r in rows]


@router.get("/featured")
def list_featured_products(db: Session = Depends(get_db)):
    """Up to 8 featured + published products for the homepage."""
    products = (
        db.query(Product)
        .filter(
            Product.is_published == True,  # noqa: E712
            Product.is_featured == True,
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
        .order_by(Product.id.desc())
        .limit(8)
        .all()
    )
    return [_to_shop_out(p, db) for p in products]
