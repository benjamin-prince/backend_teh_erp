# app/modules/containers/router.py
from __future__ import annotations
import random, string
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, distinct
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.containers.models import (
    Container, ContainerShipment, ContainerStatus, ContainerType,
    CONTAINER_TO_SHIPMENT_STATUS, CONTAINER_TO_TRACKING_EVENT,
    REQUIRES_TRACKING, REQUIRES_INVOICE,
)
from app.modules.cargo.models import Shipment, TrackingEvent

router = APIRouter(prefix="/containers", tags=["containers"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_number(db: Session, ctype: ContainerType) -> str:
    prefix = {"sea": "CONT", "air": "AIR", "groupage": "GRP"}.get(ctype.value, "CONT")
    year   = datetime.utcnow().year
    for _ in range(20):
        num = f"{prefix}-{year}-{''.join(random.choices(string.digits, k=4))}"
        if not db.execute(select(Container.id).where(Container.container_number == num)).scalar_one_or_none():
            return num
    raise HTTPException(500, "Could not generate unique container number")


def _get(db: Session, cid: int, company_id: int) -> Container:
    c = db.execute(select(Container).where(Container.id == cid, Container.company_id == company_id)).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Container not found")
    return c


def _validate(container: Container, new_status: ContainerStatus) -> None:
    """Gate: check container's own tracking/invoice fields before status advance."""
    if new_status in REQUIRES_TRACKING and not container.tracking_number:
        raise HTTPException(422, f"Carrier tracking number required before moving to '{new_status.value}'.")
    if new_status in REQUIRES_INVOICE and not container.invoice_number:
        raise HTTPException(422, f"Invoice number required before moving to '{new_status.value}'.")


def _cascade(db: Session, container: Container, new_status: ContainerStatus, user: User) -> None:
    links = db.execute(select(ContainerShipment).where(ContainerShipment.container_id == container.id)).scalars().all()
    if not links:
        return
    shipments = db.execute(select(Shipment).where(Shipment.id.in_([l.shipment_id for l in links]))).scalars().all()
    for s in shipments:
        s.status = CONTAINER_TO_SHIPMENT_STATUS[new_status]
        db.add(TrackingEvent(
            shipment_id  = s.id,
            event_type   = CONTAINER_TO_TRACKING_EVENT[new_status],
            description  = f"Container {container.container_number}" + (f" [TRK: {container.tracking_number}]" if container.tracking_number else "") + f" → {new_status.value}",
            location     = container.destination if new_status == ContainerStatus.arrived else container.depart_from,
            is_public    = True,
            created_by   = user.id,
        ))
    db.flush()


def _recalc(db: Session, container: Container) -> None:
    links = db.execute(select(ContainerShipment).where(ContainerShipment.container_id == container.id)).scalars().all()
    ids   = [l.shipment_id for l in links]
    container.packages_count  = len(ids)
    container.customers_count = (db.execute(select(func.count(distinct(Shipment.customer_id))).where(Shipment.id.in_(ids))).scalar_one() or 0) if ids else 0


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContainerCreate(BaseModel):
    container_number: Optional[str]           = None  # server-generated if omitted
    tracking_number:  Optional[str]           = None
    invoice_number:   Optional[str]           = None
    owner_name:       Optional[str]           = None
    owner_company:    Optional[str]           = None
    owner_contact:    Optional[str]           = None
    tracking_link:    Optional[str]           = None
    broker_name:      Optional[str]           = None
    broker_company:   Optional[str]           = None
    broker_contact:   Optional[str]           = None
    broker_reference: Optional[str]           = None
    type:             ContainerType           = ContainerType.sea
    status:           ContainerStatus         = ContainerStatus.preparing
    depart_from:      Optional[str]           = None
    destination:      Optional[str]           = None
    load_date:        Optional[date]          = None
    departure_date:   Optional[date]          = None
    arrival_date:     Optional[date]          = None
    total_spent:      float                   = 0
    total_earned:     float                   = 0
    currency:         str                     = "XAF"
    notes:            Optional[str]           = None


class ContainerUpdate(BaseModel):
    container_number: Optional[str]            = None
    tracking_number:  Optional[str]            = None
    invoice_number:   Optional[str]            = None
    owner_name:       Optional[str]            = None
    owner_company:    Optional[str]            = None
    owner_contact:    Optional[str]            = None
    tracking_link:    Optional[str]            = None
    broker_name:      Optional[str]            = None
    broker_company:   Optional[str]            = None
    broker_contact:   Optional[str]            = None
    broker_reference: Optional[str]            = None
    type:             Optional[ContainerType]  = None
    status:           Optional[ContainerStatus]= None
    depart_from:      Optional[str]            = None
    destination:      Optional[str]            = None
    load_date:        Optional[date]           = None
    departure_date:   Optional[date]           = None
    arrival_date:     Optional[date]           = None
    total_spent:      Optional[float]          = None
    total_earned:     Optional[float]          = None
    currency:         Optional[str]            = None
    notes:            Optional[str]            = None


class ContainerOut(BaseModel):
    id:               int
    container_number: str
    tracking_number:  Optional[str]
    invoice_number:   Optional[str]
    owner_name:       Optional[str]
    owner_company:    Optional[str]
    owner_contact:    Optional[str]
    tracking_link:    Optional[str]
    broker_name:      Optional[str]
    broker_company:   Optional[str]
    broker_contact:   Optional[str]
    broker_reference: Optional[str]
    type:             str
    status:           str
    depart_from:      Optional[str]
    destination:      Optional[str]
    load_date:        Optional[date]
    departure_date:   Optional[date]
    arrival_date:     Optional[date]
    total_spent:      float
    total_earned:     float
    currency:         str
    packages_count:   int
    customers_count:  int
    notes:            Optional[str]
    created_at:       datetime
    updated_at:       datetime
    class Config:
        from_attributes = True


class AddShipmentPayload(BaseModel):
    shipment_id: int


class ShipmentOut(BaseModel):
    id:                  int
    tracking_number:     Optional[str]
    customer_id:         int
    shipment_type:       str
    route:               str
    status:              str
    receiver_name:       Optional[str]
    receiver_phone:      Optional[str]
    receiver_country:    Optional[str]
    weight_kg:           Optional[float]
    declared_value:      Optional[float]
    content_description: Optional[str]
    created_at:          datetime
    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/generate-number")
def generate_number(type: ContainerType = Query(ContainerType.sea), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"container_number": _gen_number(db, type)}


@router.get("", response_model=List[ContainerOut])
def list_containers(
    status: Optional[str] = Query(None), type: Optional[str] = Query(None),
    search: Optional[str] = Query(None), skip: int = Query(0), limit: int = Query(100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    q = select(Container).where(Container.company_id == current_user.company_id)
    if status:
        try: q = q.where(Container.status == ContainerStatus(status))
        except ValueError: pass
    if type:
        try: q = q.where(Container.type == ContainerType(type))
        except ValueError: pass
    if search:
        like = f"%{search}%"
        q = q.where(
            Container.container_number.ilike(like) | Container.tracking_number.ilike(like) |
            Container.invoice_number.ilike(like)   | Container.depart_from.ilike(like)     |
            Container.destination.ilike(like)      | Container.owner_name.ilike(like)       |
            Container.owner_company.ilike(like)    | Container.broker_name.ilike(like)      |
            Container.broker_company.ilike(like)
        )
    return db.execute(q.order_by(Container.created_at.desc()).offset(skip).limit(limit)).scalars().all()


@router.post("", response_model=ContainerOut, status_code=status.HTTP_201_CREATED)
def create_container(payload: ContainerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    number = payload.container_number or _gen_number(db, payload.type)
    if db.execute(select(Container.id).where(Container.container_number == number)).scalar_one_or_none():
        raise HTTPException(409, f"Container number '{number}' already exists")
    dummy = Container(tracking_number=payload.tracking_number, invoice_number=payload.invoice_number)
    _validate(dummy, payload.status)
    c = Container(
        company_id=current_user.company_id, branch_id=current_user.branch_id, created_by=current_user.id,
        container_number=number,
        tracking_number=payload.tracking_number,  invoice_number=payload.invoice_number,
        owner_name=payload.owner_name,            owner_company=payload.owner_company,
        owner_contact=payload.owner_contact,      tracking_link=payload.tracking_link,
        broker_name=payload.broker_name,          broker_company=payload.broker_company,
        broker_contact=payload.broker_contact,    broker_reference=payload.broker_reference,
        type=payload.type, status=payload.status,
        depart_from=payload.depart_from,          destination=payload.destination,
        load_date=payload.load_date,              departure_date=payload.departure_date,
        arrival_date=payload.arrival_date,        total_spent=payload.total_spent,
        total_earned=payload.total_earned,        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(c); db.commit(); db.refresh(c)
    return c


@router.get("/{cid}", response_model=ContainerOut)
def get_container(cid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get(db, cid, current_user.company_id)


@router.patch("/{cid}", response_model=ContainerOut)
def update_container(cid: int, payload: ContainerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    container = _get(db, cid, current_user.company_id)
    data = payload.model_dump(exclude_unset=True)
    new_status_val = data.pop("status", None)
    # Apply field changes first so tracking/invoice updates are visible to validation
    for k, v in data.items():
        setattr(container, k, v)
    if new_status_val:
        new_status = ContainerStatus(new_status_val)
        if new_status != container.status:
            _validate(container, new_status)
            container.status = new_status
            if new_status == ContainerStatus.closed:
                container.closed_at = datetime.utcnow()
            _cascade(db, container, new_status, current_user)
    db.commit(); db.refresh(container)
    return container


@router.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container(cid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = _get(db, cid, current_user.company_id)
    db.delete(c); db.commit()


@router.get("/{cid}/shipments", response_model=List[ShipmentOut])
def list_shipments(cid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _get(db, cid, current_user.company_id)
    links = db.execute(select(ContainerShipment).where(ContainerShipment.container_id == cid)).scalars().all()
    if not links:
        return []
    return db.execute(select(Shipment).where(Shipment.id.in_([l.shipment_id for l in links])).order_by(Shipment.created_at.desc())).scalars().all()


@router.post("/{cid}/shipments", status_code=status.HTTP_201_CREATED)
def add_shipment(cid: int, payload: AddShipmentPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    container = _get(db, cid, current_user.company_id)
    shipment  = db.execute(select(Shipment).where(Shipment.id == payload.shipment_id, Shipment.company_id == current_user.company_id)).scalar_one_or_none()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    if shipment.status == "draft":
        raise HTTPException(422, f"Shipment #{shipment.id} is a draft. Confirm it first.")
    if db.execute(select(ContainerShipment).where(ContainerShipment.container_id == cid, ContainerShipment.shipment_id == payload.shipment_id)).scalar_one_or_none():
        raise HTTPException(409, "Shipment already in this container")
    db.add(ContainerShipment(container_id=cid, shipment_id=payload.shipment_id, added_by=current_user.id))
    shipment.status = CONTAINER_TO_SHIPMENT_STATUS[container.status]
    db.add(TrackingEvent(
        shipment_id=shipment.id, event_type=CONTAINER_TO_TRACKING_EVENT[container.status],
        description=f"Loaded into container {container.container_number}" + (f" [TRK: {container.tracking_number}]" if container.tracking_number else ""),
        location=container.depart_from, is_public=True, created_by=current_user.id,
    ))
    db.flush(); _recalc(db, container); db.commit()
    return {"detail": "Shipment added", "shipment_id": shipment.id}


@router.delete("/{cid}/shipments/{sid}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shipment(cid: int, sid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    container = _get(db, cid, current_user.company_id)
    link = db.execute(select(ContainerShipment).where(ContainerShipment.container_id == cid, ContainerShipment.shipment_id == sid)).scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Shipment not in this container")
    db.delete(link); db.flush(); _recalc(db, container); db.commit()