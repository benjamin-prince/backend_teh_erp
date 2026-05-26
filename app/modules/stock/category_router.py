"""TEHTEK — Product Category CRUD (authenticated)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.modules.stock.models import ProductCategory
from app.modules.stock.schemas import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(
    prefix="/stock/categories",
    tags=["stock-categories"],
    dependencies=[Depends(get_current_user)],
)


def _get_cat(db: Session, key: str) -> ProductCategory:
    cat = db.query(ProductCategory).filter_by(key=key, deleted_at=None).first()
    if not cat:
        raise HTTPException(404, f"Category '{key}' not found")
    return cat


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return (
        db.query(ProductCategory)
        .filter(ProductCategory.deleted_at.is_(None))
        .order_by(ProductCategory.sort_order, ProductCategory.key)
        .all()
    )


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(ProductCategory).filter_by(key=body.key, deleted_at=None).first():
        raise HTTPException(409, f"Category key '{body.key}' already exists")
    cat = ProductCategory(**body.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.patch("/{key}", response_model=CategoryOut)
def update_category(key: str, body: CategoryUpdate, db: Session = Depends(get_db)):
    cat = _get_cat(db, key)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{key}", status_code=204)
def delete_category(key: str, db: Session = Depends(get_db)):
    cat = _get_cat(db, key)
    cat.deleted_at = datetime.utcnow()
    db.commit()
