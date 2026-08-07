"""TEHTEK — Cargo Router. ACC-007: auth at router level."""
import hashlib
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.security import verify_password
from app.modules.cargo.models import Shipment, TrackingEvent, Bag, CarrierAssignment, PickupRequest
from app.modules.finance.models import Invoice
from app.modules.companies.controller import next_sequence
from app.core.enums import ShipmentStatus, SequenceType, BagStatus, InvoiceStatus

# SR-003: statuses that require a fully-paid invoice
_RELEASE_STATUSES = {ShipmentStatus.out_for_delivery, ShipmentStatus.delivered}

def _assert_invoice_paid(shipment_id: int, db: Session, override_user=None) -> None:
    """SR-003 king rule: raise 400 if the shipment has an unpaid invoice."""
    invoice = (
        db.query(Invoice)
        .filter_by(ref_model="shipment", ref_id=shipment_id, deleted_at=None)
        .order_by(Invoice.id.desc())
        .first()
    )
    if invoice is None:
        raise HTTPException(
            400,
            "SR-003: No invoice found for this shipment. Create and mark it paid before releasing."
        )
    if invoice.status not in (InvoiceStatus.paid,):
        raise HTTPException(
            400,
            f"SR-003: Invoice {invoice.invoice_number} is '{invoice.status.value}' "
            f"(balance due: {invoice.balance_due} {invoice.currency}). "
            "Mark the invoice as paid before releasing the shipment."
        )

MAX_PHOTOS_PER_ITEM  = 5
MAX_PHOTOS_PER_EVENT = 10

router = APIRouter(
    prefix="/api/v1",
    tags=["cargo"],
    dependencies=[Depends(get_current_user)],
)

# ── Schemas (inline for conciseness) ─────────────────────────────────────────

class ShipmentCreate(BaseModel):
    customer_id: int
    shipment_type: str
    route: str = ""               # deprecated — stored as route_legacy; use cargo_route_id
    cargo_route_id: Optional[int] = None
    receiver_name:     Optional[str] = None
    receiver_phone:    Optional[str] = None
    receiver_address:  Optional[str] = None
    receiver_city:     Optional[str] = None
    receiver_quartier: Optional[str] = None
    receiver_country:  Optional[str] = None
    content_description: Optional[str] = None
    declared_value: Optional[float] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    insurance_status: Optional[str] = None
    insured_value: Optional[float] = None
    # Pickup / delivery selection drives the available workflow steps
    pickup_type:      Optional[str] = None  # warehouse_dropoff | pickup_request | agent_collection
    pickup_location:  Optional[str] = None  # which TEHTEK location (when warehouse_dropoff)
    delivery_type:    Optional[str] = None  # door_delivery | warehouse_pickup | agency_pickup
    delivery_location: Optional[str] = None  # which TEHTEK location (when warehouse_pickup / agency_pickup)

class ShipmentUpdate(BaseModel):
    sender_name:  Optional[str] = None
    sender_phone: Optional[str] = None
    receiver_name:     Optional[str] = None
    receiver_phone:    Optional[str] = None
    receiver_address:  Optional[str] = None
    receiver_city:     Optional[str] = None
    receiver_quartier: Optional[str] = None
    receiver_country:  Optional[str] = None
    weight_kg:   Optional[float] = None
    weight_unit: Optional[str]   = None
    length_cm:   Optional[float] = None
    width_cm:    Optional[float] = None
    height_cm:   Optional[float] = None
    dim_unit:    Optional[str]   = None
    insurance_status:       Optional[str]   = None
    insured_value:          Optional[float] = None
    insured_value_currency: Optional[str]   = None
    declared_value:          Optional[float] = None
    declared_value_currency: Optional[str]  = None
    customs_value:       Optional[float] = None
    content_description: Optional[str]   = None
    notes:               Optional[str]   = None
    flat_rate:          Optional[float] = None
    flat_rate_currency: Optional[str]   = None
    pickup_type:       Optional[str] = None
    pickup_location:   Optional[str] = None
    delivery_type:     Optional[str] = None
    delivery_location: Optional[str] = None
    cargo_route_id:    Optional[int] = None

class DeclarationAccept(BaseModel):
    ip_address: Optional[str] = None

class TrackingEventPhoto(BaseModel):
    url: str
    public_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class TrackingEventCreate(BaseModel):
    event_type: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_public: bool = True
    photos: List[TrackingEventPhoto] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_photos(self):
        if len(self.photos) > MAX_PHOTOS_PER_EVENT:
            raise ValueError(f"At most {MAX_PHOTOS_PER_EVENT} photos per checkpoint")
        return self

class BagCreate(BaseModel):
    bag_type: str
    route: Optional[str] = None
    notes: Optional[str] = None

class CarrierAssign(BaseModel):
    carrier_type: str
    full_name: str
    id_number: str
    flight_number: Optional[str] = None
    departure_date: Optional[datetime] = None
    destination: Optional[str] = None
    phone: str
    max_weight_kg: Optional[float] = None

# ── Shipments ─────────────────────────────────────────────────────────────────

@router.post("/shipments", status_code=201)
def create_shipment(
    body: ShipmentCreate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:create")),
):
    data = body.model_dump()
    data["route_legacy"] = data.pop("route", "")   # rename: route → route_legacy
    s = Shipment(
        **data,
        company_id=current_user.company_id,
        branch_id=current_user.branch_id,
        created_by=current_user.id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.get("/shipments")
def list_shipments(
    status: Optional[str] = None, skip: int = 0, limit: int = 50,
    tracking_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:read")),
):
    q = db.query(Shipment).filter(
        Shipment.company_id == current_user.company_id,
        Shipment.deleted_at.is_(None)
    )
    if status:
        q = q.filter(Shipment.status == status)
    if tracking_number:
        q = q.filter(Shipment.tracking_number == tracking_number.upper())
    shipments = q.offset(skip).limit(limit).all()
    from app.modules.customers.models import Customer
    result = []
    for s in shipments:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        cust = db.query(Customer).filter_by(id=s.customer_id).first()
        d["customer"] = {"id": cust.id, "full_name": cust.full_name} if cust else None
        result.append(d)
    return result

@router.get("/shipments/{shipment_id}")
def get_shipment(
    shipment_id: int, db: Session = Depends(get_db),
    _=Depends(require_permission("cargo:read")),
):
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    from app.modules.customers.models import Customer
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    cust = db.query(Customer).filter_by(id=s.customer_id).first()
    d["customer"] = {"id": cust.id, "full_name": cust.full_name, "phone": cust.phone} if cust else None
    return d

@router.patch("/shipments/{shipment_id}")
def update_shipment(
    shipment_id: int, body: ShipmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cargo:update")),
):
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(404, "Shipment not found")

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    from app.modules.customers.models import Customer
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    cust = db.query(Customer).filter_by(id=s.customer_id).first()
    d["customer"] = {"id": cust.id, "full_name": cust.full_name, "phone": cust.phone} if cust else None
    return d

@router.post("/shipments/{shipment_id}/confirm")
def confirm_shipment(
    shipment_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:update")),
):
    """SR-002: generates tracking number. SR-008: declaration must be accepted."""
    s = db.query(Shipment).filter_by(id=shipment_id).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    if not s.declaration_accepted:
        raise HTTPException(400, "Customer must accept the liability declaration (SR-008) before confirmation")
    s.tracking_number = next_sequence(db, SequenceType.tracking_number, s.route_legacy or "")
    s.status = ShipmentStatus.confirmed
    db.commit()
    # Log tracking event
    db.add(TrackingEvent(
        shipment_id=s.id, event_type="order_created",
        description="Shipment confirmed. Tracking number assigned.",
        created_by=current_user.id,
    ))
    db.commit()
    return s

class ReleaseBody(BaseModel):
    override_reason: Optional[str] = None   # required if overriding unpaid invoice

@router.post("/shipments/{shipment_id}/release")
def release_shipment(
    shipment_id: int,
    body: ReleaseBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:update")),
):
    """SR-003: move shipment to out_for_delivery. Requires paid invoice.
    Users with can_approve_shipment_release may override with a mandatory reason."""
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(404, "Shipment not found")

    can_override = getattr(current_user, "is_superadmin", False) or \
        any(getattr(pf, "permission_key", None) == "can_approve_shipment_release"
            and getattr(pf, "is_granted", False)
            for pf in getattr(current_user, "permission_flags", []))

    if can_override and body.override_reason:
        # Allowed override — log it but proceed
        db.add(TrackingEvent(
            shipment_id=s.id,
            event_type="shipment_released",
            description=f"[OVERRIDE] Released before full payment. Reason: {body.override_reason}",
            created_by=current_user.id,
        ))
    else:
        _assert_invoice_paid(shipment_id, db)

    s.status = ShipmentStatus.out_for_delivery
    s.updated_at = datetime.utcnow()
    db.add(TrackingEvent(
        shipment_id=s.id,
        event_type="shipment_released",
        description="Shipment released for delivery.",
        created_by=current_user.id,
    ))
    db.commit()
    db.refresh(s)
    return s

@router.post("/shipments/{shipment_id}/accept-declaration")
def accept_declaration(
    shipment_id: int, body: DeclarationAccept,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    """SR-008: customer accepts liability. Logs timestamp + IP."""
    s = db.query(Shipment).filter_by(id=shipment_id).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    s.declaration_accepted = True
    s.declaration_ip = body.ip_address
    s.declaration_at = datetime.utcnow()
    db.commit()
    return {"message": "Declaration accepted", "timestamp": s.declaration_at}

@router.post("/shipments/{shipment_id}/prohibited-check")
def confirm_prohibited_check(
    shipment_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:tracking_update")),
):
    """SR-009: warehouse staff confirms prohibited item check."""
    s = db.query(Shipment).filter_by(id=shipment_id).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    s.prohibited_check_done = True
    s.status = ShipmentStatus.warehoused
    db.add(TrackingEvent(
        shipment_id=s.id, event_type="warehoused",
        description="Prohibited item check completed. Package accepted into warehouse.",
        created_by=current_user.id,
    ))
    db.commit()
    return s

# ── Tracking ──────────────────────────────────────────────────────────────────

@router.post("/shipments/{shipment_id}/tracking", status_code=201)
def add_tracking_event(
    shipment_id: int, body: TrackingEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:tracking_update")),
):
    event = TrackingEvent(
        shipment_id=shipment_id, **body.model_dump(), created_by=current_user.id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/shipments/{shipment_id}/tracking")
def get_tracking(shipment_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(TrackingEvent).filter_by(shipment_id=shipment_id).order_by(
        TrackingEvent.created_at.asc()
    ).all()

# ── Bags ──────────────────────────────────────────────────────────────────────

@router.post("/bags", status_code=201)
def create_bag(
    body: BagCreate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:bags")),
):
    bag_number = next_sequence(db, SequenceType.bag_number)
    bag = Bag(
        company_id=current_user.company_id,
        bag_number=bag_number,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(bag)
    db.commit()
    db.refresh(bag)
    return bag

@router.get("/bags")
def list_bags(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:bags")),
):
    return db.query(Bag).filter_by(company_id=current_user.company_id).all()

@router.post("/bags/{bag_id}/seal")
def seal_bag(
    bag_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:bags")),
):
    """CB-001: validate all packages have tracking + weight before sealing."""
    bag = db.query(Bag).filter_by(id=bag_id).first()
    if not bag:
        raise HTTPException(404, "Bag not found")
    # Check all packages in bag have required fields
    incomplete = db.query(Shipment).filter(
        Shipment.bag_id == bag_id,
        (Shipment.tracking_number.is_(None)) | (Shipment.weight_kg.is_(None))
    ).count()
    if incomplete:
        raise HTTPException(400, f"{incomplete} package(s) missing tracking number or weight (CB-001)")
    bag.status = BagStatus.sealed
    bag.sealed_at = datetime.utcnow()
    bag.manifest_locked = True
    db.commit()
    return bag

@router.post("/bags/{bag_id}/assign-carrier")
def assign_carrier(
    bag_id: int, body: CarrierAssign,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:travelers")),
):
    """CB-002: all traveler fields required."""
    bag = db.query(Bag).filter_by(id=bag_id).first()
    if not bag:
        raise HTTPException(404, "Bag not found")
    if bag.status != BagStatus.sealed:
        raise HTTPException(400, "Bag must be sealed before assigning a carrier")
    assignment = CarrierAssignment(bag_id=bag_id, created_by=current_user.id, **body.model_dump())
    db.add(assignment)
    bag.status = BagStatus.assigned_to_carrier
    db.commit()
    return assignment


# ── Shipment Items ─────────────────────────────────────────────────────────────

class PhotoIn(BaseModel):
    url:       str
    public_id: Optional[str] = None
    width:     Optional[int] = None
    height:    Optional[int] = None

class ShipmentItemIn(BaseModel):
    description: str
    quantity:    float = 1
    unit:        str   = "pcs"
    weight_kg:   Optional[float] = None
    weight_unit: Optional[str]   = None   # "kg" | "lbs" — original entry unit
    notes:       Optional[str]   = None
    sort_order:  int              = 0

    # Per-item delivery
    tracking_number:   Optional[str] = None
    destination:       Optional[str] = None
    receiver_name:     Optional[str] = None
    receiver_phone:    Optional[str] = None
    receiver_quartier: Optional[str] = None
    receiver_city:     Optional[str] = None

    # Packing type
    packing_type_id: Optional[int] = None

    # Dimensions (stored in cm, original unit preserved)
    length_cm:   Optional[float] = None
    width_cm:    Optional[float] = None
    height_cm:   Optional[float] = None
    dim_unit:    Optional[str]   = None   # "cm" | "in"

    # Pricing
    unit_price:     Optional[float] = None
    price_currency: Optional[str]   = None

    # Car fields
    is_car:       bool            = False
    vin:          Optional[str]   = None
    make:         Optional[str]   = None
    model:        Optional[str]   = None
    year:         Optional[int]   = None
    color:        Optional[str]   = None
    mileage_km:   Optional[int]   = None
    engine:       Optional[str]   = None
    transmission: Optional[str]   = None
    fuel_type:    Optional[str]   = None
    title_ready:  Optional[bool]  = None
    no_lien:      Optional[bool]  = None
    is_drivable:  Optional[bool]  = None
    options_text: Optional[str]   = None

    photos: List[PhotoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self):
        if len(self.photos) > MAX_PHOTOS_PER_ITEM:
            raise ValueError(f"At most {MAX_PHOTOS_PER_ITEM} photos per item")
        if self.is_car:
            missing = [f for f in ("vin", "make", "model", "year") if not getattr(self, f)]
            if missing:
                raise ValueError(f"Car items require: {', '.join(missing)}")
            if self.vin and not (11 <= len(self.vin.strip()) <= 17):
                raise ValueError("VIN must be 11–17 characters")
            if self.year and not (1900 <= self.year <= datetime.utcnow().year + 1):
                raise ValueError("Year out of range")
        return self

class ShipmentItemOut(BaseModel):
    model_config = {"from_attributes": True}
    id:          int
    shipment_id: int
    description: str
    quantity:    float
    unit:        str
    weight_kg:   Optional[float]
    weight_unit: Optional[str]
    notes:       Optional[str]
    sort_order:  int

    tracking_number:   Optional[str]
    destination:       Optional[str]
    receiver_name:     Optional[str]
    receiver_phone:    Optional[str]
    receiver_quartier: Optional[str]
    receiver_city:     Optional[str]
    packing_type_id:   Optional[int]

    length_cm:      Optional[float]
    width_cm:       Optional[float]
    height_cm:      Optional[float]
    dim_unit:       Optional[str]
    unit_price:     Optional[float]
    price_currency: Optional[str]

    is_car:       bool
    vin:          Optional[str]
    make:         Optional[str]
    model:        Optional[str]
    year:         Optional[int]
    color:        Optional[str]
    mileage_km:   Optional[int]
    engine:       Optional[str]
    transmission: Optional[str]
    fuel_type:    Optional[str]
    title_ready:  Optional[bool]
    no_lien:      Optional[bool]
    is_drivable:  Optional[bool]
    options_text: Optional[str]

    photos: List[Dict[str, Any]] = []

@router.get("/shipments/{shipment_id}/items", response_model=list[ShipmentItemOut])
def list_shipment_items(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.modules.cargo.models import ShipmentItem
    return db.query(ShipmentItem).filter_by(shipment_id=shipment_id).order_by(ShipmentItem.sort_order).all()

def _item_tracking(shipment: Shipment, db: Session) -> str:
    return next_sequence(db, SequenceType.tracking_number, shipment.route_legacy or "")


@router.post("/shipments/{shipment_id}/items", response_model=ShipmentItemOut, status_code=201)
def create_shipment_item(
    shipment_id: int,
    body: ShipmentItemIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    shipment = db.query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    from app.modules.cargo.models import ShipmentItem
    data = body.model_dump()
    if not data.get("tracking_number"):
        base = (shipment.tracking_number or "").strip()
        existing = db.query(ShipmentItem).filter_by(shipment_id=shipment_id).count()
        data["tracking_number"] = f"{base}-{existing + 1}" if base else _item_tracking(shipment, db)
    item = ShipmentItem(shipment_id=shipment_id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.put("/shipments/{shipment_id}/items", response_model=list[ShipmentItemOut])
def replace_shipment_items(
    shipment_id: int,
    body: list[ShipmentItemIn],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    shipment = db.query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    from app.modules.cargo.models import ShipmentItem
    db.query(ShipmentItem).filter_by(shipment_id=shipment_id).delete()
    # Each package/article is a child of this shipment, so number it under the
    # parent tracking number: TRK-...-000251-1, -2, ... in draft order. This keeps
    # grouped packages visibly tied to their shipment and stops item tracking from
    # consuming the global shipment sequence (which produced bogus TRK-...-000252).
    base = (shipment.tracking_number or "").strip()
    items = []
    for i, it in enumerate(body):
        data = it.model_dump()
        data["tracking_number"] = f"{base}-{i + 1}" if base else _item_tracking(shipment, db)
        items.append(ShipmentItem(shipment_id=shipment_id, **data))
    db.add_all(items)
    db.commit()
    return db.query(ShipmentItem).filter_by(shipment_id=shipment_id).order_by(ShipmentItem.sort_order).all()

@router.get("/shipments/{shipment_id}/invoice")
def get_shipment_invoice(
    shipment_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cargo:read")),
):
    """Return the latest non-cancelled invoice for this shipment, or 404."""
    from app.modules.finance.models import Invoice
    inv = (
        db.query(Invoice)
        .filter_by(ref_model="shipment", ref_id=shipment_id, deleted_at=None)
        .filter(Invoice.status != "cancelled")
        .order_by(Invoice.id.desc())
        .first()
    )
    if not inv:
        raise HTTPException(404, "No invoice for this shipment")
    from app.modules.finance.models import Payment
    payments = db.query(Payment).filter_by(invoice_id=inv.id).all()
    d = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
    d["payments"] = [
        {c.name: getattr(p, c.name) for c in p.__table__.columns}
        for p in payments
    ]
    return d


class ShipmentInvoiceCreate(BaseModel):
    subtotal:        float
    tax_amount:      float = 0
    discount_amount: float = 0
    currency:        str   = "XAF"
    notes:           Optional[str] = None
    line_items_json: Optional[str] = None


@router.post("/shipments/{shipment_id}/invoice", status_code=201)
def create_shipment_invoice(
    shipment_id: int,
    body: ShipmentInvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:update")),
):
    """Create or return existing invoice for this shipment."""
    from app.modules.finance.models import Invoice
    from app.core.enums import InvoiceType
    # If one already exists, return it
    existing = (
        db.query(Invoice)
        .filter_by(ref_model="shipment", ref_id=shipment_id, deleted_at=None)
        .filter(Invoice.status != "cancelled")
        .order_by(Invoice.id.desc())
        .first()
    )
    if existing:
        return {c.name: getattr(existing, c.name) for c in existing.__table__.columns}
    shipment = db.query(Shipment).filter_by(id=shipment_id).first()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    from app.modules.companies.controller import next_sequence
    from app.core.enums import SequenceType
    number = next_sequence(db, SequenceType.invoice_number)
    total = body.subtotal + body.tax_amount - body.discount_amount
    inv = Invoice(
        company_id=current_user.company_id,
        branch_id=current_user.branch_id,
        invoice_number=number,
        invoice_type=InvoiceType.shipment,
        customer_id=shipment.customer_id,
        ref_model="shipment",
        ref_id=shipment_id,
        subtotal=body.subtotal,
        tax_amount=body.tax_amount,
        discount_amount=body.discount_amount,
        total=total,
        balance_due=total,
        currency=body.currency,
        notes=body.notes,
        line_items_json=body.line_items_json,
        created_by=current_user.id,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return {c.name: getattr(inv, c.name) for c in inv.__table__.columns}


class ShipmentPaymentBody(BaseModel):
    invoice_id:     int
    amount:         float
    payment_method: str   = "cash"
    currency:       str   = "XAF"
    reference:      Optional[str] = None
    notes:          Optional[str] = None


@router.post("/shipments/{shipment_id}/payment", status_code=201)
def record_shipment_payment(
    shipment_id: int,
    body: ShipmentPaymentBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:update")),
):
    """Record a payment against this shipment's invoice."""
    from app.modules.finance.models import Invoice, Payment
    from app.core.enums import PaymentStatus
    inv = db.query(Invoice).filter_by(id=body.invoice_id, deleted_at=None).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    from app.modules.companies.controller import next_sequence
    from app.core.enums import SequenceType
    from datetime import datetime as _dt
    receipt_number = next_sequence(db, SequenceType.receipt_number)
    payment = Payment(
        company_id=current_user.company_id,
        invoice_id=body.invoice_id,
        customer_id=inv.customer_id,
        receipt_number=receipt_number,
        payment_method=body.payment_method,
        amount=body.amount,
        currency=body.currency,
        reference=body.reference,
        notes=body.notes,
        status=PaymentStatus.confirmed,
        created_by=current_user.id,
        confirmed_by=current_user.id,
        confirmed_at=_dt.utcnow(),
    )
    db.add(payment)
    inv.paid_amount = float(inv.paid_amount or 0) + body.amount
    inv.balance_due = float(inv.total) - float(inv.paid_amount)
    if inv.balance_due <= 0:
        inv.status = "paid"
        inv.paid_at = _dt.utcnow()
    elif float(inv.paid_amount) > 0:
        inv.status = "partial"
    inv.updated_at = _dt.utcnow()
    db.commit()
    db.refresh(payment)
    d = {c.name: getattr(payment, c.name) for c in payment.__table__.columns}
    d["invoice"] = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
    return d


@router.delete("/shipments/{shipment_id}/items/{item_id}", status_code=204)
def delete_shipment_item(
    shipment_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.modules.cargo.models import ShipmentItem
    item = db.query(ShipmentItem).filter_by(id=item_id, shipment_id=shipment_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()


# ── Cloudinary signed upload ──────────────────────────────────────────────────
#
# Frontend flow:
#   1. POST /uploads/cloudinary-signature  →  { signature, timestamp, api_key,
#                                              cloud_name, folder }
#   2. Browser uploads file directly to
#      https://api.cloudinary.com/v1_1/{cloud_name}/image/upload
#      with multipart form: file, api_key, timestamp, signature, folder
#   3. Browser receives { secure_url, public_id, width, height } and stores it
#      in the ShipmentItem.photos array.

class CloudinarySignRequest(BaseModel):
    folder: Optional[str] = None  # override default folder

class CloudinarySignResponse(BaseModel):
    signature:  str
    timestamp:  int
    api_key:    str
    cloud_name: str
    folder:     str

@router.post("/uploads/cloudinary-signature", response_model=CloudinarySignResponse)
def cloudinary_signature(
    body: CloudinarySignRequest,
    current_user=Depends(get_current_user),
):
    """Return a short-lived signed payload for direct browser → Cloudinary upload."""
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
        raise HTTPException(503, "Cloudinary not configured")

    folder    = (body.folder or settings.CLOUDINARY_UPLOAD_FOLDER).strip("/")
    timestamp = int(time.time())

    # Signature = sha1( "<param1>=<value1>&...&<api_secret>" )
    # with params sorted alphabetically (folder, timestamp here).
    to_sign   = f"folder={folder}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    return CloudinarySignResponse(
        signature=signature,
        timestamp=timestamp,
        api_key=settings.CLOUDINARY_API_KEY,
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        folder=folder,
    )


class DeleteShipmentRequest(BaseModel):
    password: str

@router.delete("/shipments/{shipment_id}", status_code=204)
def delete_shipment(
    shipment_id: int,
    body: DeleteShipmentRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently soft-delete a shipment after password confirmation."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Incorrect password")
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    now = datetime.utcnow()
    s.deleted_at = now
    # Also soft-delete related invoice
    inv = db.query(Invoice).filter_by(ref_model="shipment", ref_id=shipment_id, deleted_at=None).first()
    if inv:
        inv.deleted_at = now
    db.commit()
