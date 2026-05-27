from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import StockStatus
from app.modules.stock.models import Product, Warehouse, StockItem, StockMovement


CAT_PREFIX: dict[str, str] = {
    "electronics":        "ELE",
    "it_equipment":       "IT",
    "printer":            "PRN",
    "network_equipment":  "NET",
    "security_equipment": "SEC",
    "solar_equipment":    "SOL",
    "storage":            "STG",
    "telecom":            "TEL",
    "tv_av":              "TVA",
    "accessories":        "ACC",
    "consumable":         "CON",
    "office_supplies":    "OFF",
    "pc_peripherals":     "PCP",
    "pc_components":      "PCM",
    "raw_material":       "RAW",
    "finished_good":      "FIN",
    "spare_part":         "SPA",
    "packaging":          "PKG",
    # legacy aliases kept for existing SKUs
    "solar":              "SOL",
    "security":           "SEC",
    "networking":         "NET",
    "cables":             "CAB",
    "consumables":        "CON",
    "cargo_supplies":     "CGO",
    "other":              "OTH",
}

SUBCATEGORIES: dict[str, list[str]] = {
    # ── current enum values ────────────────────────────────────────────────
    "electronics":        ["smartphone", "tablet", "smartwatch", "camera", "audio", "gaming", "component", "other"],
    "it_equipment":       ["laptop", "desktop", "all_in_one", "server", "workstation", "other"],
    "printer":            ["inkjet", "laser", "multifunction", "label_printer", "plotter", "scanner", "other"],
    "network_equipment":  ["router", "switch", "access_point", "sfp_module", "firewall", "modem", "antenna", "cable", "other"],
    "security_equipment": ["ip_camera", "nvr_dvr", "access_control", "alarm", "sensor", "intercom", "cable", "other"],
    "solar_equipment":    ["panel", "battery", "inverter", "charge_controller", "ups", "mounting", "cable", "other"],
    "storage":            ["hdd", "ssd", "nas", "usb_drive", "memory_card", "tape", "other"],
    "telecom":            ["ip_phone", "pabx", "voip_gateway", "headset", "conference", "other"],
    "tv_av":              ["tv", "projector", "audio_system", "set_top_box", "screen", "other"],
    "accessories":        ["bag", "case", "mouse", "keyboard", "monitor_stand", "hub", "adapter", "cable", "other"],
    "consumable":         ["ink_cartridge", "toner", "paper", "battery_aa", "cleaning_kit", "other"],
    "office_supplies":    ["furniture", "stationery", "whiteboard", "shredder", "other"],
    "raw_material":       ["other"],
    "finished_good":      ["other"],
    "pc_peripherals":     ["monitor", "keyboard", "mouse", "webcam", "speaker", "headset", "numpad", "hub", "docking", "other"],
    "pc_components":      ["cpu", "ram", "gpu", "motherboard", "psu", "cooling", "case", "ssd_m2", "hdd_int", "other"],
    "spare_part":         ["other"],
    "packaging":          ["box", "tape", "bubble_wrap", "label", "pallet", "strap", "other"],
    # ── legacy aliases (old frontend still sends these) ────────────────────
    "solar":              ["panel", "battery", "inverter", "charge_controller", "mounting", "cable", "other"],
    "security":           ["ip_camera", "nvr_dvr", "access_control", "alarm", "sensor", "cable", "other"],
    "networking":         ["router", "switch", "access_point", "sfp_module", "firewall", "cable", "other"],
    "cables":             ["hdmi", "usb", "ethernet", "power", "fiber", "coaxial", "display_port", "other"],
    "consumables":        ["ink_cartridge", "toner", "paper", "battery_aa", "cleaning_kit", "other"],
    "cargo_supplies":     ["box", "tape", "bubble_wrap", "label", "pallet", "strap", "other"],
    "other":              ["other"],
}

UNITS = ["pcs", "kg", "g", "m", "cm", "l", "ml", "box", "set", "pair", "roll", "sheet"]


def generate_sku(db: Session, category: str, brand: str | None, company_id: int) -> str:
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

    candidate = f"{prefix}{count + 1:04d}"

    while db.query(Product).filter_by(sku=candidate, company_id=company_id).first():
        count += 1
        candidate = f"{prefix}{count + 1:04d}"

    return candidate


def product_out(p: Product) -> dict:
    return {
        "id": p.id,
        "company_id": p.company_id,
        "sku": p.sku,
        "barcode": p.barcode,
        "model_number": p.model_number,
        "name": p.name,
        "name_fr": p.name_fr,
        "description": p.description,
        "brand": p.brand,
        "category": p.category,
        "subcategory": p.subcategory,
        "tags": p.tags,
        "unit": p.unit,
        "weight_kg": float(p.weight_kg) if p.weight_kg else None,
        "cost_price": float(p.cost_price) if p.cost_price else None,
        "selling_price": float(p.sell_price) if p.sell_price else None,
        "tax_rate": float(p.tax_rate) if p.tax_rate else 19.25,
        "reorder_level": p.reorder_level if p.reorder_level is not None else 5,
        "min_order_qty": p.min_order_qty if p.min_order_qty is not None else 1,
        "warranty_months": p.warranty_months,
        "is_active": p.is_active,
        "is_published": bool(p.is_published) if p.is_published is not None else False,
        "is_featured": bool(p.is_featured) if p.is_featured is not None else False,
        "compare_price": float(p.compare_price) if p.compare_price else None,
        "image_url": p.image_url,
        "image_urls": p.image_urls or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def stock_item_out(item: StockItem) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "warehouse_id": item.warehouse_id,
        "quantity": item.quantity,
        "reserved": item.reserved_qty,
        "available": item.available_qty,
        "min_quantity": item.min_quantity,
        "status": item.status,
    }


def movement_out(mv: StockMovement, product_id: int) -> dict:
    return {
        "id": mv.id,
        "product_id": product_id,
        "stock_item_id": mv.stock_item_id,
        "movement_type": mv.movement_type,
        "quantity": mv.quantity,
        "reason": mv.reason,
        "created_at": mv.created_at.isoformat() if mv.created_at else None,
    }


def get_or_create_stock_item(db: Session, product: Product, company_id: int) -> StockItem:
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


def validate_subcategory(category: str, subcategory: str | None) -> None:
    if not subcategory:
        return

    valid = SUBCATEGORIES.get(category, [])
    if subcategory not in valid:
        raise HTTPException(
            400,
            f"Invalid subcategory '{subcategory}' for category '{category}'. Valid: {valid}",
        )


def update_stock_status(item: StockItem) -> None:
    if item.quantity == 0:
        item.status = StockStatus.out_of_stock
    elif item.quantity < item.min_quantity:
        item.status = StockStatus.low_stock
    else:
        item.status = StockStatus.in_stock
