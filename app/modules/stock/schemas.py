from typing import Optional

from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    category: str

    sku: Optional[str] = None
    barcode: Optional[str] = None
    model_number: Optional[str] = None

    name_fr: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None

    subcategory: Optional[str] = None
    tags: Optional[str] = None

    unit: str = "pcs"
    weight_kg: Optional[float] = None

    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    tax_rate: float = 19.25

    reorder_level: int = 5
    min_order_qty: int = 1
    warranty_months: Optional[int] = None

    condition: str = "new"

    is_active: bool = True
    is_published: bool = False
    is_featured: bool = False
    compare_price: Optional[float] = None
    image_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    name_fr: Optional[str] = None
    brand: Optional[str] = None

    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[str] = None

    unit: Optional[str] = None
    weight_kg: Optional[float] = None

    barcode: Optional[str] = None
    model_number: Optional[str] = None
    description: Optional[str] = None

    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    tax_rate: Optional[float] = None

    reorder_level: Optional[int] = None
    min_order_qty: Optional[int] = None
    warranty_months: Optional[int] = None

    condition: Optional[str] = None

    is_active: Optional[bool] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    compare_price: Optional[float] = None
    image_url: Optional[str] = None


# ── Public shop schema (no cost_price, no internal fields) ────────────────────

class ShopProductOut(BaseModel):
    id: int
    sku: str
    name: str
    name_fr: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    tags: Optional[str] = None
    sell_price: Optional[float] = None
    compare_price: Optional[float] = None
    warranty_months: Optional[int] = None
    image_url: Optional[str] = None
    is_featured: bool
    stock_available: int  # total available qty across all warehouses

    class Config:
        from_attributes = True


class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: str
    quantity: float
    reason: Optional[str] = None


class StockAdjust(BaseModel):
    quantity: int
    reason: str


class ReservationCreate(BaseModel):
    customer_id: int
    quantity: int
    order_id: Optional[int] = None
