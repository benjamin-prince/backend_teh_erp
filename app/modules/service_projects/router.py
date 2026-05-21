"""
app/modules/service_projects/router.py
All routes are protected (require valid JWT).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.modules.service_projects import controller as ctrl
from app.modules.service_projects.models import ServiceProjectStatus
from app.modules.service_projects.schemas import (
    ServiceTypeCreate, ServiceTypeUpdate, ServiceTypeOut,
    ServiceProjectCreate, ServiceProjectUpdate, ServiceProjectOut,
    MilestoneCreate, MilestoneUpdate, MilestoneOut,
    SkipBrPayload,
)

router = APIRouter(
    prefix="/api/v1/service-projects",
    tags=["service-projects"],
    dependencies=[Depends(get_current_user)],
)


# ── Service Types ─────────────────────────────────────────────────────────────

@router.get("/types", response_model=List[ServiceTypeOut])
def list_types(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    return ctrl.list_service_types(db, active_only=active_only)


@router.post("/types", response_model=ServiceTypeOut, status_code=201)
def create_type(payload: ServiceTypeCreate, db: Session = Depends(get_db)):
    return ctrl.create_service_type(db, payload)


@router.patch("/types/{type_id}", response_model=ServiceTypeOut)
def update_type(
    type_id: int,
    payload: ServiceTypeUpdate,
    db: Session = Depends(get_db),
):
    return ctrl.update_service_type(db, type_id, payload)


@router.delete("/types/{type_id}", status_code=204)
def delete_type(type_id: int, db: Session = Depends(get_db)):
    ctrl.delete_service_type(db, type_id)


# ── Service Projects ──────────────────────────────────────────────────────────

@router.get("", response_model=List[ServiceProjectOut])
def list_projects(
    customer_id:      Optional[int]                  = Query(None),
    status:           Optional[ServiceProjectStatus] = Query(None),
    category:         Optional[str]                  = Query(None),
    exclude_category: Optional[str]                  = Query(None),
    skip:             int = Query(0, ge=0),
    limit:            int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return ctrl.list_projects(
        db,
        customer_id=customer_id,
        status=status,
        category=category,
        exclude_category=exclude_category,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ServiceProjectOut, status_code=201)
def create_project(payload: ServiceProjectCreate, db: Session = Depends(get_db)):
    return ctrl.create_project(db, payload)


@router.get("/{project_id}", response_model=ServiceProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return ctrl.get_project(db, project_id)


@router.patch("/{project_id}", response_model=ServiceProjectOut)
def update_project(
    project_id: int,
    payload: ServiceProjectUpdate,
    db: Session = Depends(get_db),
):
    return ctrl.update_project(db, project_id, payload)


@router.post("/{project_id}/skip-br", response_model=ServiceProjectOut)
def skip_br(
    project_id: int,
    payload: SkipBrPayload,
    db: Session = Depends(get_db),
):
    return ctrl.skip_br(db, project_id, payload)


# ── Invoice sub-resource ──────────────────────────────────────────────────────

@router.post("/{project_id}/invoice", status_code=201)
def generate_invoice(project_id: int, db: Session = Depends(get_db)):
    inv = ctrl.generate_invoice(db, project_id)
    return {
        "id":             inv.id,
        "invoice_number": inv.invoice_number,
        "total":          float(inv.total),
        "status":         inv.status,
    }


@router.get("/{project_id}/invoice")
def get_invoice(project_id: int, db: Session = Depends(get_db)):
    inv = ctrl.get_invoice(db, project_id)
    return {
        "id":             inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id":    inv.customer_id,
        "subtotal":       float(inv.subtotal),
        "discount_amount":float(inv.discount_amount),
        "tax_amount":     float(inv.tax_amount),
        "total":          float(inv.total),
        "paid_amount":    float(inv.paid_amount),
        "balance_due":    float(inv.balance_due),
        "status":         inv.status,
        "line_items_json":inv.line_items_json,
        "notes":          inv.notes,
        "created_at":     inv.created_at.isoformat(),
    }


# ── Milestones ────────────────────────────────────────────────────────────────

@router.get("/{project_id}/milestones", response_model=List[MilestoneOut])
def list_milestones(project_id: int, db: Session = Depends(get_db)):
    return ctrl.list_milestones(db, project_id)


@router.post("/{project_id}/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(
    project_id: int,
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
):
    return ctrl.create_milestone(db, project_id, payload)


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    project_id:   int,
    milestone_id: int,
    payload: MilestoneUpdate,
    db: Session = Depends(get_db),
):
    return ctrl.update_milestone(db, project_id, milestone_id, payload)


@router.delete("/{project_id}/milestones/{milestone_id}", status_code=204)
def delete_milestone(
    project_id:   int,
    milestone_id: int,
    db: Session = Depends(get_db),
):
    ctrl.delete_milestone(db, project_id, milestone_id)
