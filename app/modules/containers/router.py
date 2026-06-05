from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import verify_password
from app.modules.cargo.models import Shipment, TrackingEvent
from app.modules.finance.models import Invoice
from app.modules.containers.models import (
    CONTAINER_TO_SHIPMENT_STATUS,
    CONTAINER_TO_TRACKING_EVENT,
    REQUIRES_INVOICE,
    REQUIRES_TRACKING,
    Broker,
    Container,
    ContainerShipment,
    ContainerStatus,
    ContainerType,
    ShippingLine,
)
from app.modules.containers.service import generate_container_number
from app.modules.users.models import User


router = APIRouter(prefix="/api/v1/containers", tags=["containers"])


def _invoice_for(db: Session, shipment_id: int) -> dict | None:
    inv = db.execute(
        select(Invoice)
        .where(
            Invoice.ref_model == "shipment",
            Invoice.ref_id == shipment_id,
            Invoice.deleted_at.is_(None),
            Invoice.cancelled_at.is_(None),
        )
        .order_by(Invoice.id.desc())
    ).scalar_one_or_none()
    if not inv:
        return None
    return {
        "invoice_total":  float(inv.total or 0),
        "invoice_paid":   float(inv.paid_amount or 0),
        "invoice_status": inv.status,
        "invoice_currency": inv.currency,
    }


def _get(db: Session, cid: int, company_id: int) -> Container:
    container = db.execute(
        select(Container).where(
            Container.id == cid,
            Container.company_id == company_id,
        )
    ).scalar_one_or_none()

    if not container:
        raise HTTPException(404, "Container not found")

    return container


def _validate(container: Container, new_status: ContainerStatus) -> None:
    if new_status in REQUIRES_TRACKING and not container.tracking_number:
        raise HTTPException(
            422,
            f"Carrier tracking number required before moving to '{new_status.value}'.",
        )

    if new_status in REQUIRES_INVOICE and not container.invoice_number:
        raise HTTPException(
            422,
            f"Invoice number required before moving to '{new_status.value}'.",
        )


def _cascade(
    db: Session,
    container: Container,
    new_status: ContainerStatus,
    user: User,
) -> None:
    links = db.execute(
        select(ContainerShipment).where(
            ContainerShipment.container_id == container.id
        )
    ).scalars().all()

    if not links:
        return

    shipment_ids = [link.shipment_id for link in links]

    shipments = db.execute(
        select(Shipment).where(Shipment.id.in_(shipment_ids))
    ).scalars().all()

    for shipment in shipments:
        shipment.status = CONTAINER_TO_SHIPMENT_STATUS[new_status]

        db.add(
            TrackingEvent(
                shipment_id=shipment.id,
                event_type=CONTAINER_TO_TRACKING_EVENT[new_status],
                description=(
                    f"Container {container.container_number}"
                    + (
                        f" [TRK: {container.tracking_number}]"
                        if container.tracking_number
                        else ""
                    )
                    + f" → {new_status.value}"
                ),
                location=(
                    container.destination
                    if new_status == ContainerStatus.arrived
                    else container.depart_from
                ),
                is_public=True,
                created_by=user.id,
            )
        )

    db.flush()


def _recalc(db: Session, container: Container) -> None:
    links = db.execute(
        select(ContainerShipment).where(
            ContainerShipment.container_id == container.id
        )
    ).scalars().all()

    shipment_ids = [link.shipment_id for link in links]

    container.packages_count = len(shipment_ids)

    if shipment_ids:
        container.customers_count = (
            db.execute(
                select(func.count(distinct(Shipment.customer_id))).where(
                    Shipment.id.in_(shipment_ids)
                )
            ).scalar_one()
            or 0
        )

        # Sum invoice totals across all shipments → total_earned
        invoices = db.execute(
            select(Invoice).where(
                Invoice.ref_model == "shipment",
                Invoice.ref_id.in_(shipment_ids),
                Invoice.deleted_at.is_(None),
                Invoice.cancelled_at.is_(None),
            )
        ).scalars().all()

        container.total_earned = sum(float(inv.total or 0) for inv in invoices)

        # Update container currency to match invoices if they share one
        currencies = list({inv.currency for inv in invoices if inv.currency})
        if len(currencies) == 1:
            container.currency = currencies[0]
    else:
        container.customers_count = 0
        container.total_earned = 0


class ShippingLineEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    tracking_url_template: Optional[str]


class BrokerEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    company_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]


class LocationEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    city: Optional[str] = None
    country: Optional[str] = None


class CargoRouteEmbed(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str] = None
    origin_country: Optional[str] = None
    dest_country: Optional[str] = None
    transport_mode: Optional[str] = None
    origin_location: Optional[LocationEmbed] = None
    dest_location: Optional[LocationEmbed] = None


class ContainerCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    container_number: Optional[str] = None
    tracking_number: Optional[str] = None
    invoice_number: Optional[str] = None

    shipping_line_id: Optional[int] = None
    owner_company: Optional[str] = None
    tracking_link: Optional[str] = None

    broker_id: Optional[int] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_contact: Optional[str] = None
    broker_reference: Optional[str] = None

    type: ContainerType = ContainerType.sea
    status: ContainerStatus = ContainerStatus.preparing

    cargo_route_id: Optional[int] = None
    depart_from: Optional[str] = None
    destination: Optional[str] = None
    load_date: Optional[date] = None
    departure_date: Optional[date] = None
    arrival_date: Optional[date] = None

    total_spent: float = 0
    total_earned: float = 0
    currency: str = "XAF"
    notes: Optional[str] = None


class ContainerUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    container_number: Optional[str] = None
    tracking_number: Optional[str] = None
    invoice_number: Optional[str] = None

    shipping_line_id: Optional[int] = None
    owner_company: Optional[str] = None
    tracking_link: Optional[str] = None

    broker_id: Optional[int] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_contact: Optional[str] = None
    broker_reference: Optional[str] = None

    type: Optional[ContainerType] = None
    status: Optional[ContainerStatus] = None

    cargo_route_id: Optional[int] = None
    depart_from: Optional[str] = None
    destination: Optional[str] = None
    load_date: Optional[date] = None
    departure_date: Optional[date] = None
    arrival_date: Optional[date] = None

    total_spent: Optional[float] = None
    total_earned: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class ContainerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    container_number: str
    tracking_number: Optional[str]
    invoice_number: Optional[str]

    shipping_line_id: Optional[int]
    shipping_line: Optional[ShippingLineEmbed]
    owner_company: Optional[str]
    tracking_link: Optional[str]

    broker_id: Optional[int]
    broker: Optional[BrokerEmbed]
    broker_name: Optional[str]
    broker_company: Optional[str]
    broker_contact: Optional[str]
    broker_reference: Optional[str]

    type: str
    status: str

    cargo_route_id: Optional[int] = None
    cargo_route: Optional[CargoRouteEmbed] = None
    depart_from: Optional[str]
    destination: Optional[str]
    load_date: Optional[date]
    departure_date: Optional[date]
    arrival_date: Optional[date]

    total_spent: float
    total_earned: float
    total_receivable: float = 0   # sum of invoice totals
    total_paid: float = 0         # sum of invoice paid amounts
    currency: str
    packages_count: int
    customers_count: int

    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class AddShipmentPayload(BaseModel):
    shipment_id: int


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_number: Optional[str]
    customer_id: int
    shipment_type: str
    route: Optional[str] = None
    route_legacy: Optional[str] = None
    status: str
    receiver_name: Optional[str]
    receiver_phone: Optional[str]
    receiver_country: Optional[str]
    weight_kg: Optional[float]
    declared_value: Optional[float]
    content_description: Optional[str]
    created_at: datetime


@router.get("/generate-number")
def generate_number(
    type: ContainerType = Query(ContainerType.sea),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return {"container_number": generate_container_number(db, type)}


@router.get("", response_model=List[ContainerOut])
def list_containers(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Container).where(Container.company_id == current_user.company_id)

    if status:
        try:
            query = query.where(Container.status == ContainerStatus(status))
        except ValueError:
            pass

    if type:
        try:
            query = query.where(Container.type == ContainerType(type))
        except ValueError:
            pass

    if search:
        like = f"%{search}%"
        query = query.where(
            Container.container_number.ilike(like)
            | Container.tracking_number.ilike(like)
            | Container.invoice_number.ilike(like)
            | Container.depart_from.ilike(like)
            | Container.destination.ilike(like)
            | Container.owner_name.ilike(like)
            | Container.owner_company.ilike(like)
            | Container.broker_name.ilike(like)
            | Container.broker_company.ilike(like)
        )

    return (
        db.execute(
            query.order_by(Container.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )


@router.post("", response_model=ContainerOut, status_code=status.HTTP_201_CREATED)
def create_container(
    payload: ContainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dummy = Container(
        tracking_number=payload.tracking_number,
        invoice_number=payload.invoice_number,
    )
    _validate(dummy, payload.status)

    for _ in range(3):
        try:
            number = payload.container_number or generate_container_number(
                db,
                payload.type,
            )

            if db.execute(
                select(Container.id).where(Container.container_number == number)
            ).scalar_one_or_none():
                payload.container_number = None
                continue

            # Resolve shipping line and broker for denormalization
            sl = None
            if payload.shipping_line_id:
                sl = db.execute(
                    select(ShippingLine).where(ShippingLine.id == payload.shipping_line_id)
                ).scalar_one_or_none()

            broker = None
            if payload.broker_id:
                broker = db.execute(
                    select(Broker).where(Broker.id == payload.broker_id)
                ).scalar_one_or_none()

            container = Container(
                company_id=current_user.company_id,
                branch_id=getattr(current_user, "branch_id", None),
                created_by=current_user.id,
                container_number=number,
                tracking_number=payload.tracking_number,
                invoice_number=payload.invoice_number,
                shipping_line_id=payload.shipping_line_id,
                owner_company=sl.name if sl else payload.owner_company,
                tracking_link=payload.tracking_link,
                broker_id=payload.broker_id,
                broker_name=broker.name if broker else payload.broker_name,
                broker_company=broker.company_name if broker else payload.broker_company,
                broker_contact=broker.phone if broker else payload.broker_contact,
                broker_reference=payload.broker_reference,
                type=payload.type,
                status=payload.status,
                cargo_route_id=payload.cargo_route_id,
                depart_from=payload.depart_from,
                destination=payload.destination,
                load_date=payload.load_date,
                departure_date=payload.departure_date,
                arrival_date=payload.arrival_date,
                total_spent=payload.total_spent,
                total_earned=payload.total_earned,
                currency=payload.currency,
                notes=payload.notes,
            )

            db.add(container)
            db.commit()
            db.refresh(container)
            return container

        except IntegrityError:
            db.rollback()
            payload.container_number = None

    raise HTTPException(500, "Failed to generate unique container number")


@router.get("/{cid}")
def get_container(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    container = _get(db, cid, current_user.company_id)
    links = db.execute(
        select(ContainerShipment.shipment_id).where(ContainerShipment.container_id == cid)
    ).scalars().all()
    invoices = db.execute(
        select(Invoice).where(
            Invoice.ref_model == "shipment",
            Invoice.ref_id.in_(links),
            Invoice.deleted_at.is_(None),
            Invoice.cancelled_at.is_(None),
        )
    ).scalars().all() if links else []
    total_receivable = sum(float(inv.total or 0) for inv in invoices)
    total_paid       = sum(float(inv.paid_amount or 0) for inv in invoices)
    currencies = list({inv.currency for inv in invoices if inv.currency})
    currency = currencies[0] if len(currencies) == 1 else container.currency
    d = {c.name: getattr(container, c.name) for c in container.__table__.columns}
    d["shipping_line"] = None
    d["broker"] = None
    d["total_receivable"] = total_receivable
    d["total_paid"] = total_paid
    d["currency"] = currency
    r = container.cargo_route
    if r:
        def _loc(loc):
            if not loc: return None
            return {"id": loc.id, "name": loc.name, "city": getattr(loc, "city", None), "country": getattr(loc, "country", None)}
        d["cargo_route"] = {
            "id": r.id, "name": r.name, "code": r.code,
            "origin_country": r.origin_country, "dest_country": r.dest_country,
            "transport_mode": r.transport_mode,
            "origin_location": _loc(r.origin_location),
            "dest_location": _loc(r.dest_location),
        }
    else:
        d["cargo_route"] = None
    return d


@router.patch("/{cid}", response_model=ContainerOut)
def update_container(
    cid: int,
    payload: ContainerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    container = _get(db, cid, current_user.company_id)
    data = payload.model_dump(exclude_unset=True)

    new_status_value = data.pop("status", None)

    # Re-denormalize if shipping_line_id or broker_id changes
    if "shipping_line_id" in data:
        sl_id = data["shipping_line_id"]
        if sl_id:
            sl = db.execute(select(ShippingLine).where(ShippingLine.id == sl_id)).scalar_one_or_none()
            if sl:
                data.setdefault("owner_company", sl.name)
        else:
            data.setdefault("owner_company", None)

    if "broker_id" in data:
        b_id = data["broker_id"]
        if b_id:
            b = db.execute(select(Broker).where(Broker.id == b_id)).scalar_one_or_none()
            if b:
                data.setdefault("broker_name",    b.name)
                data.setdefault("broker_company",  b.company_name)
                data.setdefault("broker_contact",  b.phone)
        else:
            data.setdefault("broker_name",    None)
            data.setdefault("broker_company", None)
            data.setdefault("broker_contact", None)

    for key, value in data.items():
        setattr(container, key, value)

    if new_status_value:
        new_status = ContainerStatus(new_status_value)

        if new_status != container.status:
            _validate(container, new_status)
            container.status = new_status

            if new_status == ContainerStatus.closed:
                container.closed_at = datetime.utcnow()

            _cascade(db, container, new_status, current_user)

    db.commit()
    db.refresh(container)

    return container


class DeletePasswordBody(BaseModel):
    password: str

@router.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container(
    cid: int,
    body: DeletePasswordBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Incorrect password")
    container = _get(db, cid, current_user.company_id)
    db.delete(container)
    db.commit()


@router.get("/{cid}/shipments")
def list_shipments(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get(db, cid, current_user.company_id)

    links = db.execute(
        select(ContainerShipment).where(ContainerShipment.container_id == cid)
    ).scalars().all()

    if not links:
        return []

    shipment_ids = [link.shipment_id for link in links]

    shipments = db.execute(
        select(Shipment)
        .where(Shipment.id.in_(shipment_ids))
        .order_by(Shipment.created_at.desc())
    ).scalars().all()

    from app.modules.customers.models import Customer
    result = []
    for s in shipments:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        cust = db.execute(select(Customer).where(Customer.id == s.customer_id)).scalar_one_or_none()
        d["customer"] = {"id": cust.id, "full_name": cust.full_name} if cust else None
        inv = _invoice_for(db, s.id)
        d.update(inv or {"invoice_total": None, "invoice_paid": None, "invoice_status": None, "invoice_currency": None})
        result.append(d)
    return result


@router.get("/{cid}/available-shipments")
def available_shipments(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shipments not linked to ANY container for this company, not drafts."""
    _get(db, cid, current_user.company_id)

    in_any_container = db.execute(
        select(ContainerShipment.shipment_id)
        .join(Container, Container.id == ContainerShipment.container_id)
        .where(Container.company_id == current_user.company_id)
    ).scalars().all()

    q = (
        select(Shipment)
        .where(
            Shipment.company_id == current_user.company_id,
            Shipment.deleted_at.is_(None),
            Shipment.status != "draft",
        )
    )
    if in_any_container:
        q = q.where(Shipment.id.notin_(in_any_container))

    shipments = db.execute(q.order_by(Shipment.route_legacy, Shipment.created_at.desc())).scalars().all()

    from app.modules.customers.models import Customer
    result = []
    for s in shipments:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        cust = db.execute(select(Customer).where(Customer.id == s.customer_id)).scalar_one_or_none()
        d["customer"] = {"id": cust.id, "full_name": cust.full_name} if cust else None
        inv = _invoice_for(db, s.id)
        d.update(inv or {"invoice_total": None, "invoice_paid": None, "invoice_status": None, "invoice_currency": None})
        result.append(d)
    return result


@router.post("/{cid}/shipments", status_code=status.HTTP_201_CREATED)
def add_shipment(
    cid: int,
    payload: AddShipmentPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    container = _get(db, cid, current_user.company_id)

    shipment = db.execute(
        select(Shipment).where(
            Shipment.id == payload.shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()

    if not shipment:
        raise HTTPException(404, "Shipment not found")

    if shipment.status == "draft":
        raise HTTPException(422, f"Shipment #{shipment.id} is a draft. Confirm it first.")

    exists = db.execute(
        select(ContainerShipment).where(
            ContainerShipment.container_id == cid,
            ContainerShipment.shipment_id == payload.shipment_id,
        )
    ).scalar_one_or_none()

    if exists:
        raise HTTPException(409, "Shipment already in this container")

    db.add(
        ContainerShipment(
            container_id=cid,
            shipment_id=payload.shipment_id,
            added_by=current_user.id,
        )
    )

    shipment.status = CONTAINER_TO_SHIPMENT_STATUS[container.status]

    db.add(
        TrackingEvent(
            shipment_id=shipment.id,
            event_type=CONTAINER_TO_TRACKING_EVENT[container.status],
            description=(
                f"Loaded into container {container.container_number}"
                + (
                    f" [TRK: {container.tracking_number}]"
                    if container.tracking_number
                    else ""
                )
            ),
            location=container.depart_from,
            is_public=True,
            created_by=current_user.id,
        )
    )

    db.flush()
    _recalc(db, container)
    db.commit()

    return {"detail": "Shipment added", "shipment_id": shipment.id}


@router.delete("/{cid}/shipments/{sid}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shipment(
    cid: int,
    sid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    container = _get(db, cid, current_user.company_id)

    link = db.execute(
        select(ContainerShipment).where(
            ContainerShipment.container_id == cid,
            ContainerShipment.shipment_id == sid,
        )
    ).scalar_one_or_none()

    if not link:
        raise HTTPException(404, "Shipment not in this container")

    db.delete(link)
    db.flush()
    _recalc(db, container)
    db.commit()
