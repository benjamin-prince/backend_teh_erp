"""TEHTEK — Auto-Parc Router. ACC-007: auth at router level."""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.autopark.models import (
    Vehicle, FuelLog, VehicleMaintenance, VehicleDocument, VehicleAssignment
)
from app.modules.finance.extended_models import Location

router = APIRouter(
    prefix="/api/v1/autopark",
    tags=["autopark"],
    dependencies=[Depends(get_current_user)],
)

DOC_ALERT_DAYS = 30       # documents expiring within N days show up in alerts
MAINT_ALERT_DAYS = 14     # planned maintenance due within N days


# ── Schemas ───────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    name: str
    vehicle_type: str = "car"
    usage_type: str = "business"   # business | personal | rental | sale
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    registration_plate: Optional[str] = None
    vin: Optional[str] = None
    fuel_type: str = "essence"
    tank_capacity_l: Optional[float] = None
    current_odometer_km: float = 0
    status: str = "active"
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    currency: str = "XAF"
    assigned_location_id: Optional[int] = None
    assigned_driver_name: Optional[str] = None
    assigned_driver_phone: Optional[str] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None

class VehicleUpdate(BaseModel):
    name: Optional[str] = None
    vehicle_type: Optional[str] = None
    usage_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    registration_plate: Optional[str] = None
    vin: Optional[str] = None
    fuel_type: Optional[str] = None
    tank_capacity_l: Optional[float] = None
    current_odometer_km: Optional[float] = None
    status: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    currency: Optional[str] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None

class FuelLogCreate(BaseModel):
    vehicle_id: int
    log_date: date
    liters: float
    total_cost: float
    odometer_km: Optional[float] = None
    price_per_liter: Optional[float] = None
    currency: str = "XAF"
    full_tank: bool = True
    station: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None

class FuelLogUpdate(BaseModel):
    log_date: Optional[date] = None
    liters: Optional[float] = None
    total_cost: Optional[float] = None
    odometer_km: Optional[float] = None
    price_per_liter: Optional[float] = None
    currency: Optional[str] = None
    full_tank: Optional[bool] = None
    station: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None

class MaintenanceCreate(BaseModel):
    vehicle_id: int
    title: str
    maintenance_type: str = "autre"
    description: Optional[str] = None
    status: str = "planned"
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    odometer_km: Optional[float] = None
    cost: float = 0
    currency: str = "XAF"
    garage_name: Optional[str] = None
    invoice_ref: Optional[str] = None
    next_due_date: Optional[date] = None
    next_due_km: Optional[float] = None
    notes: Optional[str] = None

class MaintenanceUpdate(BaseModel):
    title: Optional[str] = None
    maintenance_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    odometer_km: Optional[float] = None
    cost: Optional[float] = None
    currency: Optional[str] = None
    garage_name: Optional[str] = None
    invoice_ref: Optional[str] = None
    next_due_date: Optional[date] = None
    next_due_km: Optional[float] = None
    notes: Optional[str] = None

class DocumentCreate(BaseModel):
    vehicle_id: int
    doc_type: str
    reference: Optional[str] = None
    provider: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    cost: float = 0
    currency: str = "XAF"
    file_url: Optional[str] = None
    notes: Optional[str] = None

class DocumentUpdate(BaseModel):
    doc_type: Optional[str] = None
    reference: Optional[str] = None
    provider: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    cost: Optional[float] = None
    currency: Optional[str] = None
    file_url: Optional[str] = None
    notes: Optional[str] = None

class AssignmentCreate(BaseModel):
    location_id: Optional[int] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    start_date: Optional[date] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_vehicle(db: Session, company_id: int, vehicle_id: int) -> Vehicle:
    v = db.query(Vehicle).filter_by(
        id=vehicle_id, company_id=company_id, deleted_at=None
    ).first()
    if not v:
        raise HTTPException(404, "Vehicle not found")
    return v


def _location_name(db: Session, location_id: Optional[int]) -> Optional[str]:
    if not location_id:
        return None
    loc = db.query(Location).filter_by(id=location_id).first()
    return loc.name if loc else None


def _vehicle_out(db: Session, v: Vehicle) -> dict:
    return {
        "id": v.id,
        "name": v.name,
        "vehicle_type": v.vehicle_type,
        "usage_type": v.usage_type,
        "brand": v.brand,
        "model": v.model,
        "year": v.year,
        "color": v.color,
        "registration_plate": v.registration_plate,
        "vin": v.vin,
        "fuel_type": v.fuel_type,
        "tank_capacity_l": float(v.tank_capacity_l) if v.tank_capacity_l is not None else None,
        "current_odometer_km": float(v.current_odometer_km or 0),
        "status": v.status,
        "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
        "purchase_price": float(v.purchase_price) if v.purchase_price is not None else None,
        "currency": v.currency,
        "assigned_location_id": v.assigned_location_id,
        "assigned_location_name": _location_name(db, v.assigned_location_id),
        "assigned_driver_name": v.assigned_driver_name,
        "assigned_driver_phone": v.assigned_driver_phone,
        "photo_url": v.photo_url,
        "notes": v.notes,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


# ── Summary & Alerts ──────────────────────────────────────────────────────────

@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cid = current_user.company_id
    today = date.today()
    month_start = today.replace(day=1)

    vehicles = db.query(Vehicle).filter_by(company_id=cid, deleted_at=None).all()
    total = len(vehicles)
    active = sum(1 for v in vehicles if v.status == "active")
    in_maint = sum(1 for v in vehicles if v.status == "in_maintenance")

    fuel_month = db.query(func.coalesce(func.sum(FuelLog.total_cost), 0)).filter(
        FuelLog.company_id == cid,
        FuelLog.log_date >= month_start,
        FuelLog.currency == "XAF",
    ).scalar()

    maint_month = db.query(func.coalesce(func.sum(VehicleMaintenance.cost), 0)).filter(
        VehicleMaintenance.company_id == cid,
        VehicleMaintenance.status == "done",
        VehicleMaintenance.completed_date >= month_start,
        VehicleMaintenance.currency == "XAF",
    ).scalar()

    expiring_docs = db.query(VehicleDocument).filter(
        VehicleDocument.company_id == cid,
        VehicleDocument.deleted_at.is_(None),
        VehicleDocument.expiry_date.isnot(None),
        VehicleDocument.expiry_date <= today + timedelta(days=DOC_ALERT_DAYS),
    ).count()

    return {
        "total_vehicles": total,
        "active_vehicles": active,
        "in_maintenance": in_maint,
        "out_of_service": sum(1 for v in vehicles if v.status == "out_of_service"),
        "fuel_cost_month_xaf": float(fuel_month or 0),
        "maintenance_cost_month_xaf": float(maint_month or 0),
        "expiring_documents": expiring_docs,
    }


@router.get("/alerts")
def alerts(
    days: int = DOC_ALERT_DAYS,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Documents expiring soon / expired + maintenance due soon."""
    cid = current_user.company_id
    today = date.today()
    horizon = today + timedelta(days=days)
    out = []

    docs = db.query(VehicleDocument, Vehicle).join(
        Vehicle, VehicleDocument.vehicle_id == Vehicle.id
    ).filter(
        VehicleDocument.company_id == cid,
        VehicleDocument.deleted_at.is_(None),
        Vehicle.deleted_at.is_(None),
        VehicleDocument.expiry_date.isnot(None),
        VehicleDocument.expiry_date <= horizon,
    ).order_by(VehicleDocument.expiry_date.asc()).all()

    for doc, veh in docs:
        days_left = (doc.expiry_date - today).days
        out.append({
            "kind": "document",
            "severity": "expired" if days_left < 0 else ("critical" if days_left <= 7 else "warning"),
            "vehicle_id": veh.id,
            "vehicle_name": veh.name,
            "registration_plate": veh.registration_plate,
            "doc_id": doc.id,
            "doc_type": doc.doc_type,
            "reference": doc.reference,
            "expiry_date": doc.expiry_date.isoformat(),
            "days_left": days_left,
        })

    maints = db.query(VehicleMaintenance, Vehicle).join(
        Vehicle, VehicleMaintenance.vehicle_id == Vehicle.id
    ).filter(
        VehicleMaintenance.company_id == cid,
        Vehicle.deleted_at.is_(None),
        VehicleMaintenance.status.in_(["planned", "in_progress"]),
        VehicleMaintenance.scheduled_date.isnot(None),
        VehicleMaintenance.scheduled_date <= today + timedelta(days=MAINT_ALERT_DAYS),
    ).order_by(VehicleMaintenance.scheduled_date.asc()).all()

    for m, veh in maints:
        days_left = (m.scheduled_date - today).days
        out.append({
            "kind": "maintenance",
            "severity": "expired" if days_left < 0 else ("critical" if days_left <= 3 else "warning"),
            "vehicle_id": veh.id,
            "vehicle_name": veh.name,
            "registration_plate": veh.registration_plate,
            "maintenance_id": m.id,
            "title": m.title,
            "maintenance_type": m.maintenance_type,
            "scheduled_date": m.scheduled_date.isoformat(),
            "days_left": days_left,
        })

    return out


# ── Vehicles ──────────────────────────────────────────────────────────────────

@router.get("/vehicles")
def list_vehicles(
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    usage_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Vehicle).filter(
        Vehicle.company_id == current_user.company_id,
        Vehicle.deleted_at.is_(None),
    )
    if status:
        q = q.filter(Vehicle.status == status)
    if vehicle_type:
        q = q.filter(Vehicle.vehicle_type == vehicle_type)
    if usage_type:
        q = q.filter(Vehicle.usage_type == usage_type)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            Vehicle.name.ilike(like),
            Vehicle.registration_plate.ilike(like),
            Vehicle.brand.ilike(like),
            Vehicle.model.ilike(like),
            Vehicle.assigned_driver_name.ilike(like),
        ))
    rows = q.order_by(Vehicle.created_at.desc()).offset(skip).limit(limit).all()
    return [_vehicle_out(db, v) for v in rows]


@router.post("/vehicles", status_code=201)
def create_vehicle(
    body: VehicleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if body.registration_plate:
        dup = db.query(Vehicle).filter(
            Vehicle.company_id == current_user.company_id,
            Vehicle.deleted_at.is_(None),
            Vehicle.registration_plate == body.registration_plate,
        ).first()
        if dup:
            raise HTTPException(400, f"Un véhicule avec la plaque '{body.registration_plate}' existe déjà")

    v = Vehicle(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(v)
    db.flush()

    # Open the initial assignment record if a site/driver was given
    if body.assigned_location_id or body.assigned_driver_name:
        db.add(VehicleAssignment(
            company_id=current_user.company_id,
            vehicle_id=v.id,
            location_id=body.assigned_location_id,
            driver_name=body.assigned_driver_name,
            driver_phone=body.assigned_driver_phone,
            start_date=date.today(),
            created_by=current_user.id,
        ))
    db.commit()
    db.refresh(v)
    return _vehicle_out(db, v)


@router.get("/vehicles/{vehicle_id}")
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    v = _get_vehicle(db, current_user.company_id, vehicle_id)
    return _vehicle_out(db, v)


@router.patch("/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    v = _get_vehicle(db, current_user.company_id, vehicle_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("registration_plate"):
        dup = db.query(Vehicle).filter(
            Vehicle.company_id == current_user.company_id,
            Vehicle.deleted_at.is_(None),
            Vehicle.registration_plate == data["registration_plate"],
            Vehicle.id != vehicle_id,
        ).first()
        if dup:
            raise HTTPException(400, f"Un véhicule avec la plaque '{data['registration_plate']}' existe déjà")
    for k, val in data.items():
        setattr(v, k, val)
    v.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(v)
    return _vehicle_out(db, v)


@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    v = _get_vehicle(db, current_user.company_id, vehicle_id)
    v.deleted_at = datetime.utcnow()
    db.commit()


# ── Assignment (site / driver) ────────────────────────────────────────────────

@router.get("/vehicles/{vehicle_id}/assignments")
def list_assignments(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _get_vehicle(db, current_user.company_id, vehicle_id)
    rows = db.query(VehicleAssignment).filter_by(
        vehicle_id=vehicle_id, company_id=current_user.company_id
    ).order_by(VehicleAssignment.start_date.desc(), VehicleAssignment.id.desc()).all()
    return [{
        "id": a.id,
        "location_id": a.location_id,
        "location_name": _location_name(db, a.location_id),
        "driver_name": a.driver_name,
        "driver_phone": a.driver_phone,
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "end_date": a.end_date.isoformat() if a.end_date else None,
        "notes": a.notes,
    } for a in rows]


@router.post("/vehicles/{vehicle_id}/assign", status_code=201)
def assign_vehicle(
    vehicle_id: int,
    body: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Assign the vehicle to a site and/or driver. Closes the previous open assignment."""
    v = _get_vehicle(db, current_user.company_id, vehicle_id)
    start = body.start_date or date.today()

    # Close any open assignment
    open_assignments = db.query(VehicleAssignment).filter_by(
        vehicle_id=vehicle_id, company_id=current_user.company_id, end_date=None
    ).all()
    for a in open_assignments:
        a.end_date = start

    db.add(VehicleAssignment(
        company_id=current_user.company_id,
        vehicle_id=vehicle_id,
        location_id=body.location_id,
        driver_name=body.driver_name,
        driver_phone=body.driver_phone,
        start_date=start,
        notes=body.notes,
        created_by=current_user.id,
    ))

    v.assigned_location_id = body.location_id
    v.assigned_driver_name = body.driver_name
    v.assigned_driver_phone = body.driver_phone
    v.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(v)
    return _vehicle_out(db, v)


# ── Fuel logs ─────────────────────────────────────────────────────────────────

@router.get("/fuel-logs")
def list_fuel_logs(
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(FuelLog).filter_by(company_id=current_user.company_id)
    if vehicle_id:
        q = q.filter(FuelLog.vehicle_id == vehicle_id)
    rows = q.order_by(FuelLog.log_date.desc(), FuelLog.id.desc()).offset(skip).limit(limit).all()
    return rows


@router.post("/fuel-logs", status_code=201)
def create_fuel_log(
    body: FuelLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    v = _get_vehicle(db, current_user.company_id, body.vehicle_id)
    log = FuelLog(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(log)
    # Move the vehicle odometer forward
    if body.odometer_km and float(body.odometer_km) > float(v.current_odometer_km or 0):
        v.current_odometer_km = body.odometer_km
        v.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


@router.patch("/fuel-logs/{log_id}")
def update_fuel_log(
    log_id: int,
    body: FuelLogUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    log = db.query(FuelLog).filter_by(id=log_id, company_id=current_user.company_id).first()
    if not log:
        raise HTTPException(404, "Fuel log not found")
    for k, val in body.model_dump(exclude_unset=True).items():
        setattr(log, k, val)
    log.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


@router.delete("/fuel-logs/{log_id}", status_code=204)
def delete_fuel_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    log = db.query(FuelLog).filter_by(id=log_id, company_id=current_user.company_id).first()
    if not log:
        raise HTTPException(404, "Fuel log not found")
    db.delete(log)
    db.commit()


@router.get("/vehicles/{vehicle_id}/fuel-stats")
def fuel_stats(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Totals + consumption (L/100km) computed between consecutive full-tank logs."""
    _get_vehicle(db, current_user.company_id, vehicle_id)
    logs = db.query(FuelLog).filter_by(
        vehicle_id=vehicle_id, company_id=current_user.company_id
    ).order_by(FuelLog.log_date.asc(), FuelLog.id.asc()).all()

    total_liters = sum(float(l.liters or 0) for l in logs)
    total_cost = sum(float(l.total_cost or 0) for l in logs if (l.currency or "XAF") == "XAF")

    # Consumption between consecutive full-tank logs with odometer readings
    segments = []
    prev = None
    for l in logs:
        if not l.full_tank or l.odometer_km is None:
            continue
        if prev is not None:
            dist = float(l.odometer_km) - float(prev.odometer_km)
            if dist > 0:
                per100 = float(l.liters) / dist * 100
                segments.append({
                    "from_date": prev.log_date.isoformat(),
                    "to_date": l.log_date.isoformat(),
                    "distance_km": round(dist, 1),
                    "liters": float(l.liters),
                    "l_per_100km": round(per100, 2),
                })
        prev = l

    avg = (sum(s["l_per_100km"] for s in segments) / len(segments)) if segments else None
    # Anomaly: a segment 30%+ above the vehicle average
    anomalies = [s for s in segments if avg and s["l_per_100km"] > avg * 1.3]

    return {
        "vehicle_id": vehicle_id,
        "logs_count": len(logs),
        "total_liters": round(total_liters, 1),
        "total_cost_xaf": round(total_cost, 0),
        "avg_l_per_100km": round(avg, 2) if avg else None,
        "segments": segments[-12:],
        "anomalies": anomalies,
    }


# ── Maintenance ───────────────────────────────────────────────────────────────

@router.get("/maintenance")
def list_maintenance(
    vehicle_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(VehicleMaintenance).filter_by(company_id=current_user.company_id)
    if vehicle_id:
        q = q.filter(VehicleMaintenance.vehicle_id == vehicle_id)
    if status:
        q = q.filter(VehicleMaintenance.status == status)
    return q.order_by(
        VehicleMaintenance.created_at.desc()
    ).offset(skip).limit(limit).all()


@router.post("/maintenance", status_code=201)
def create_maintenance(
    body: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _get_vehicle(db, current_user.company_id, body.vehicle_id)
    m = VehicleMaintenance(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/maintenance/{maintenance_id}")
def update_maintenance(
    maintenance_id: int,
    body: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    m = db.query(VehicleMaintenance).filter_by(
        id=maintenance_id, company_id=current_user.company_id
    ).first()
    if not m:
        raise HTTPException(404, "Maintenance not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("status") == "done" and not data.get("completed_date") and not m.completed_date:
        data["completed_date"] = date.today()
    for k, val in data.items():
        setattr(m, k, val)
    m.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(m)
    return m


@router.delete("/maintenance/{maintenance_id}", status_code=204)
def delete_maintenance(
    maintenance_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    m = db.query(VehicleMaintenance).filter_by(
        id=maintenance_id, company_id=current_user.company_id
    ).first()
    if not m:
        raise HTTPException(404, "Maintenance not found")
    db.delete(m)
    db.commit()


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents")
def list_documents(
    vehicle_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(VehicleDocument).filter(
        VehicleDocument.company_id == current_user.company_id,
        VehicleDocument.deleted_at.is_(None),
    )
    if vehicle_id:
        q = q.filter(VehicleDocument.vehicle_id == vehicle_id)
    if doc_type:
        q = q.filter(VehicleDocument.doc_type == doc_type)
    return q.order_by(
        VehicleDocument.expiry_date.asc().nullslast()
    ).offset(skip).limit(limit).all()


@router.post("/documents", status_code=201)
def create_document(
    body: DocumentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _get_vehicle(db, current_user.company_id, body.vehicle_id)
    d = VehicleDocument(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.patch("/documents/{document_id}")
def update_document(
    document_id: int,
    body: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    d = db.query(VehicleDocument).filter_by(
        id=document_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Document not found")
    for k, val in body.model_dump(exclude_unset=True).items():
        setattr(d, k, val)
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    d = db.query(VehicleDocument).filter_by(
        id=document_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Document not found")
    d.deleted_at = datetime.utcnow()
    db.commit()


# ── Full history ──────────────────────────────────────────────────────────────

@router.get("/vehicles/{vehicle_id}/history")
def vehicle_history(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Combined chronological timeline: fuel, maintenance, documents, assignments."""
    cid = current_user.company_id
    _get_vehicle(db, cid, vehicle_id)
    events = []

    for l in db.query(FuelLog).filter_by(vehicle_id=vehicle_id, company_id=cid).all():
        events.append({
            "kind": "fuel",
            "date": l.log_date.isoformat(),
            "title": f"Plein {float(l.liters):g} L",
            "detail": l.station,
            "amount": float(l.total_cost or 0),
            "currency": l.currency,
            "odometer_km": float(l.odometer_km) if l.odometer_km is not None else None,
        })

    for m in db.query(VehicleMaintenance).filter_by(vehicle_id=vehicle_id, company_id=cid).all():
        d = m.completed_date or m.scheduled_date
        events.append({
            "kind": "maintenance",
            "date": d.isoformat() if d else (m.created_at.date().isoformat() if m.created_at else None),
            "title": m.title,
            "detail": m.garage_name,
            "status": m.status,
            "amount": float(m.cost or 0),
            "currency": m.currency,
            "odometer_km": float(m.odometer_km) if m.odometer_km is not None else None,
        })

    for doc in db.query(VehicleDocument).filter(
        VehicleDocument.vehicle_id == vehicle_id,
        VehicleDocument.company_id == cid,
        VehicleDocument.deleted_at.is_(None),
    ).all():
        d = doc.issue_date or (doc.created_at.date() if doc.created_at else None)
        events.append({
            "kind": "document",
            "date": d.isoformat() if d else None,
            "title": doc.doc_type,
            "detail": doc.reference or doc.provider,
            "amount": float(doc.cost or 0),
            "currency": doc.currency,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
        })

    for a in db.query(VehicleAssignment).filter_by(vehicle_id=vehicle_id, company_id=cid).all():
        parts = []
        loc = _location_name(db, a.location_id)
        if loc:
            parts.append(loc)
        if a.driver_name:
            parts.append(a.driver_name)
        events.append({
            "kind": "assignment",
            "date": a.start_date.isoformat() if a.start_date else None,
            "title": "Affectation",
            "detail": " · ".join(parts) or None,
            "end_date": a.end_date.isoformat() if a.end_date else None,
        })

    events.sort(key=lambda e: e["date"] or "", reverse=True)
    return events
