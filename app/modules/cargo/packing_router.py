# app/modules/cargo/packing_router.py
# CRUD for PackingType (pallet, barrel, wardrobe, carton, etc.)

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User


class PackingType(Base):
    __tablename__ = "packing_types"

    id         = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    name        = Column(String(100), nullable=False)   # "Carton", "Pallet", "Barrel"
    code        = Column(String(30),  nullable=True)    # short code e.g. CTN, PLT
    # Standard dimensions (cm)
    length_cm   = Column(Numeric(8, 2), nullable=True)
    width_cm    = Column(Numeric(8, 2), nullable=True)
    height_cm   = Column(Numeric(8, 2), nullable=True)
    # Tare / empty weight (kg)
    tare_weight_kg = Column(Numeric(8, 3), nullable=True)
    # Default price charged per unit of this packing type
    default_price    = Column(Numeric(14, 2), nullable=True)
    price_currency   = Column(String(10), nullable=False, server_default="XAF")
    notes       = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


router = APIRouter(tags=["packing-types"])


class PackingTypeCreate(BaseModel):
    name:           str
    code:           Optional[str]   = None
    length_cm:      Optional[float] = None
    width_cm:       Optional[float] = None
    height_cm:      Optional[float] = None
    tare_weight_kg: Optional[float] = None
    default_price:  Optional[float] = None
    price_currency: str             = "XAF"
    notes:          Optional[str]   = None


class PackingTypeUpdate(BaseModel):
    name:           Optional[str]   = None
    code:           Optional[str]   = None
    length_cm:      Optional[float] = None
    width_cm:       Optional[float] = None
    height_cm:      Optional[float] = None
    tare_weight_kg: Optional[float] = None
    default_price:  Optional[float] = None
    price_currency: Optional[str]   = None
    notes:          Optional[str]   = None


class PackingTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             int
    name:           str
    code:           Optional[str]
    length_cm:      Optional[float]
    width_cm:       Optional[float]
    height_cm:      Optional[float]
    tare_weight_kg: Optional[float]
    default_price:  Optional[float]
    price_currency: str
    notes:          Optional[str]


@router.get("/api/v1/packing-types", response_model=List[PackingTypeOut])
def list_packing_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    return db.execute(
        select(PackingType)
        .where(PackingType.company_id == current_user.company_id)
        .order_by(PackingType.name)
    ).scalars().all()


@router.post("/api/v1/packing-types", response_model=PackingTypeOut, status_code=status.HTTP_201_CREATED)
def create_packing_type(
    payload: PackingTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pt = PackingType(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return pt


@router.patch("/api/v1/packing-types/{pt_id}", response_model=PackingTypeOut)
def update_packing_type(
    pt_id: int,
    payload: PackingTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    pt = db.execute(
        select(PackingType).where(
            PackingType.id == pt_id,
            PackingType.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not pt:
        raise HTTPException(404, "Packing type not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(pt, k, v)
    pt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pt)
    return pt


@router.delete("/api/v1/packing-types/{pt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_packing_type(
    pt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    pt = db.execute(
        select(PackingType).where(
            PackingType.id == pt_id,
            PackingType.company_id == current_user.company_id,
        )
    ).scalar_one_or_none()
    if not pt:
        raise HTTPException(404, "Packing type not found")
    db.delete(pt)
    db.commit()
