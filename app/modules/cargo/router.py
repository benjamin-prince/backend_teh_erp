"""TEHTEK — Cargo Router. ACC-007: auth at router level."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.cargo.models import Shipment, TrackingEvent, Bag, CarrierAssignment, PickupRequest
from app.modules.companies.controller import next_sequence
from app.core.enums import ShipmentStatus, SequenceType, BagStatus

router = APIRouter(
    prefix="/api/v1",
    tags=["cargo"],
    dependencies=[Depends(get_current_user)],
)

# ── Schemas (inline for conciseness) ─────────────────────────────────────────

class ShipmentCreate(BaseModel):
    customer_id: int
    shipment_type: str
    route: str
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_address: Optional[str] = None
    receiver_country: Optional[str] = None
    content_description: Optional[str] = None
    declared_value: Optional[float] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    insurance_status: Optional[str] = None
    insured_value: Optional[float] = None

class ShipmentUpdate(BaseModel):
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    insurance_status: Optional[str] = None
    insured_value: Optional[float] = None
    declared_value: Optional[float] = None
    customs_value: Optional[float] = None
    content_description: Optional[str] = None
    insurance_status: Optional[str] = None
    insured_value: Optional[float] = None
    notes: Optional[str] = None

class DeclarationAccept(BaseModel):
    ip_address: Optional[str] = None

class TrackingEventCreate(BaseModel):
    event_type: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_public: bool = True

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
    s = Shipment(
        **body.model_dump(),
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
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:read")),
):
    q = db.query(Shipment).filter(
        Shipment.company_id == current_user.company_id,
        Shipment.deleted_at.is_(None)
    )
    if status:
        q = q.filter(Shipment.status == status)
    return q.offset(skip).limit(limit).all()

@router.get("/shipments/{shipment_id}")
def get_shipment(
    shipment_id: int, db: Session = Depends(get_db),
    _=Depends(require_permission("cargo:read")),
):
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    return s

@router.patch("/shipments/{shipment_id}")
def update_shipment(
    shipment_id: int, body: ShipmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cargo:update")),
):
    s = db.query(Shipment).filter_by(id=shipment_id, deleted_at=None).first()
    if not s:
        raise HTTPException(404, "Shipment not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s

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
    s.tracking_number = next_sequence(db, SequenceType.tracking_number, s.route)
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
