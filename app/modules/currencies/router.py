from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from . import models, schemas

router = APIRouter(
    prefix="/api/v1/currencies",
    tags=["Currencies"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[schemas.CurrencyOut])
def list_currencies(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(models.Currency)
    if not include_inactive:
        q = q.filter(models.Currency.is_active == True)
    return q.order_by(models.Currency.code).all()


@router.post("", response_model=schemas.CurrencyOut, status_code=201)
def create_currency(
    data: schemas.CurrencyCreate,
    db: Session = Depends(get_db),
):
    code = data.code.upper().strip()
    if db.query(models.Currency).filter(models.Currency.code == code).first():
        raise HTTPException(400, f"Currency '{code}' already exists")
    obj = models.Currency(
        code=code,
        name=data.name,
        symbol=data.symbol,
        rate_to_xaf=data.rate_to_xaf,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{code}", response_model=schemas.CurrencyOut)
def update_currency(
    code: str,
    data: schemas.CurrencyUpdate,
    db: Session = Depends(get_db),
):
    obj = db.query(models.Currency).filter(models.Currency.code == code.upper()).first()
    if not obj:
        raise HTTPException(404, f"Currency '{code}' not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{code}", status_code=204)
def delete_currency(
    code: str,
    db: Session = Depends(get_db),
):
    obj = db.query(models.Currency).filter(models.Currency.code == code.upper()).first()
    if not obj:
        raise HTTPException(404, f"Currency '{code}' not found")
    if code.upper() == "XAF":
        raise HTTPException(400, "Cannot delete base currency XAF")
    db.delete(obj)
    db.commit()
