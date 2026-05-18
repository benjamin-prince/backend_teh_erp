"""
app/modules/service_projects/service_types_router.py

Mounts at /api/v1/service-types — the URL the frontend actually calls.
The original /api/v1/service-projects/types sub-routes are kept in router.py
for backward compatibility.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.service_projects import controller as ctrl
from app.modules.service_projects.schemas import (
    ServiceTypeCreate, ServiceTypeOut, ServiceTypeUpdate,
)

router = APIRouter(
    prefix="/api/v1/service-types",
    tags=["service-types"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[ServiceTypeOut])
def list_service_types(
    active_only: bool          = Query(True),
    category:    Optional[str] = Query(None),
    skip:        int           = Query(0,   ge=0),
    limit:       int           = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return ctrl.list_service_types(db, active_only=active_only)


@router.post("", response_model=ServiceTypeOut, status_code=201)
def create_service_type(payload: ServiceTypeCreate, db: Session = Depends(get_db)):
    return ctrl.create_service_type(db, payload)


@router.get("/{type_id}", response_model=ServiceTypeOut)
def get_service_type(type_id: int, db: Session = Depends(get_db)):
    from app.modules.service_projects.models import ServiceType
    obj = db.query(ServiceType).filter_by(id=type_id).first()
    if not obj:
        raise HTTPException(404, "Service type not found")
    return obj


@router.patch("/{type_id}", response_model=ServiceTypeOut)
def update_service_type(
    type_id: int, payload: ServiceTypeUpdate, db: Session = Depends(get_db),
):
    return ctrl.update_service_type(db, type_id, payload)


@router.delete("/{type_id}", status_code=204)
def delete_service_type(type_id: int, db: Session = Depends(get_db)):
    ctrl.delete_service_type(db, type_id)
