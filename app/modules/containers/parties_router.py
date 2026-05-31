# app/modules/containers/parties_router.py
# CRUD for ShippingLine and Broker entities

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.containers.models import Broker, ShippingLine
from app.modules.users.models import User

router = APIRouter(tags=["container-parties"])


# ── Shipping Lines ─────────────────────────────────────────────────────────────

class ShippingLineCreate(BaseModel):
    name:                  str
    code:                  Optional[str] = None
    phone:                 Optional[str] = None
    email:                 Optional[str] = None
    website:               Optional[str] = None
    tracking_url_template: Optional[str] = None
    notes:                 Optional[str] = None


class ShippingLineUpdate(BaseModel):
    name:                  Optional[str] = None
    code:                  Optional[str] = None
    phone:                 Optional[str] = None
    email:                 Optional[str] = None
    website:               Optional[str] = None
    tracking_url_template: Optional[str] = None
    notes:                 Optional[str] = None


class ShippingLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    name:                  str
    code:                  Optional[str]
    phone:                 Optional[str]
    email:                 Optional[str]
    website:               Optional[str]
    tracking_url_template: Optional[str]
    notes:                 Optional[str]


@router.get("/api/v1/shipping-lines", response_model=List[ShippingLineOut])
def list_shipping_lines(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ShippingLine).where(ShippingLine.company_id == current_user.company_id)
    if search:
        like = f"%{search}%"
        q = q.where(
            ShippingLine.name.ilike(like) | ShippingLine.code.ilike(like)
        )
    return db.execute(q.order_by(ShippingLine.name)).scalars().all()


@router.post("/api/v1/shipping-lines", response_model=ShippingLineOut, status_code=status.HTTP_201_CREATED)
def create_shipping_line(
    payload: ShippingLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sl = ShippingLine(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(sl)
    db.commit()
    db.refresh(sl)
    return sl


@router.patch("/api/v1/shipping-lines/{sl_id}", response_model=ShippingLineOut)
def update_shipping_line(
    sl_id: int,
    payload: ShippingLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sl = db.execute(
        select(ShippingLine).where(
            ShippingLine.id == sl_id,
            ShippingLine.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not sl:
        raise HTTPException(404, "Shipping line not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sl, k, v)
    db.commit()
    db.refresh(sl)
    return sl


@router.delete("/api/v1/shipping-lines/{sl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipping_line(
    sl_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sl = db.execute(
        select(ShippingLine).where(
            ShippingLine.id == sl_id,
            ShippingLine.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not sl:
        raise HTTPException(404, "Shipping line not found")
    db.delete(sl)
    db.commit()


# ── Brokers ────────────────────────────────────────────────────────────────────

class BrokerCreate(BaseModel):
    name:         str
    company_name: Optional[str] = None
    phone:        Optional[str] = None
    email:        Optional[str] = None
    notes:        Optional[str] = None


class BrokerUpdate(BaseModel):
    name:         Optional[str] = None
    company_name: Optional[str] = None
    phone:        Optional[str] = None
    email:        Optional[str] = None
    notes:        Optional[str] = None


class BrokerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    name:         str
    company_name: Optional[str]
    phone:        Optional[str]
    email:        Optional[str]
    notes:        Optional[str]


@router.get("/api/v1/brokers", response_model=List[BrokerOut])
def list_brokers(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Broker).where(Broker.company_id == current_user.company_id)
    if search:
        like = f"%{search}%"
        q = q.where(
            Broker.name.ilike(like) | Broker.company_name.ilike(like)
        )
    return db.execute(q.order_by(Broker.name)).scalars().all()


@router.post("/api/v1/brokers", response_model=BrokerOut, status_code=status.HTTP_201_CREATED)
def create_broker(
    payload: BrokerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = Broker(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.patch("/api/v1/brokers/{broker_id}", response_model=BrokerOut)
def update_broker(
    broker_id: int,
    payload: BrokerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.execute(
        select(Broker).where(
            Broker.id == broker_id,
            Broker.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Broker not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/api/v1/brokers/{broker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_broker(
    broker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.execute(
        select(Broker).where(
            Broker.id == broker_id,
            Broker.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Broker not found")
    db.delete(b)
    db.commit()
