"""
app/modules/service_projects/router.py
All routes are protected (require valid JWT).
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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

class InvoiceGeneratePayload(BaseModel):
    percentage: Optional[float] = None
    amount: Optional[float] = None


@router.post("/{project_id}/invoice", status_code=201)
def generate_invoice(project_id: int, body: Optional[InvoiceGeneratePayload] = None,
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    pct = body.percentage if body else None
    amt = body.amount if body else None
    inv = ctrl.generate_invoice(db, project_id, pct, amt, current_user.company_id, current_user.id)
    # Cumulative paid across all invoices for this project
    from app.modules.finance.models import Invoice as InvModel
    from decimal import Decimal as D
    all_invs = db.query(InvModel).filter_by(ref_model="service_project", ref_id=project_id).all()
    total_previously_paid = float(sum(D(str(i.paid_amount or 0)) for i in all_invs))

    return {
        "id":                   inv.id,
        "invoice_number":       inv.invoice_number,
        "customer_id":          inv.customer_id,
        "subtotal":             float(inv.subtotal),
        "discount_amount":      float(inv.discount_amount),
        "tax_amount":           float(inv.tax_amount),
        "total":                float(inv.total),
        "paid_amount":          float(inv.paid_amount),
        "balance_due":          float(inv.balance_due),
        "status":               inv.status,
        "line_items_json":      inv.line_items_json,
        "notes":                inv.notes,
        "created_at":           inv.created_at.isoformat(),
        "total_previously_paid": total_previously_paid,
    }


@router.get("/{project_id}/invoice")
def get_invoice(project_id: int, db: Session = Depends(get_db)):
    inv = ctrl.get_invoice(db, project_id)
    from app.modules.finance.models import Invoice as InvModel
    from decimal import Decimal as D
    all_invs = db.query(InvModel).filter_by(ref_model="service_project", ref_id=project_id).all()
    total_previously_paid = float(sum(D(str(i.paid_amount or 0)) for i in all_invs))
    return {
        "id":                    inv.id,
        "invoice_number":        inv.invoice_number,
        "customer_id":           inv.customer_id,
        "subtotal":              float(inv.subtotal),
        "discount_amount":       float(inv.discount_amount),
        "tax_amount":            float(inv.tax_amount),
        "total":                 float(inv.total),
        "paid_amount":           float(inv.paid_amount),
        "balance_due":           float(inv.balance_due),
        "status":                inv.status,
        "line_items_json":       inv.line_items_json,
        "notes":                 inv.notes,
        "created_at":            inv.created_at.isoformat(),
        "total_previously_paid": total_previously_paid,
    }


class CancelProjectBody(BaseModel):
    reason: str
    password: str

class DeleteProjectBody(BaseModel):
    password: str

@router.post("/{project_id}/cancel", status_code=200, response_model=ServiceProjectOut)
def cancel_project(project_id: int, body: CancelProjectBody,
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """Cancel a project at any stage. Requires superadmin password."""
    from app.core.security import verify_password
    if not current_user.is_superadmin:
        raise HTTPException(403, "Superadmin required")
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(403, "Incorrect password")
    project = ctrl.get_project(db, project_id)
    if project.status == ServiceProjectStatus.cancelled:
        raise HTTPException(400, "Project is already cancelled")
    project.status = ServiceProjectStatus.cancelled
    project.cancel_reason = body.reason.strip()
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, body: DeleteProjectBody,
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """Permanently delete a cancelled project. Requires superadmin password."""
    from app.core.security import verify_password
    if not current_user.is_superadmin:
        raise HTTPException(403, "Superadmin required")
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(403, "Incorrect password")
    project = ctrl.get_project(db, project_id)
    if project.status != ServiceProjectStatus.cancelled:
        raise HTTPException(400, "Only cancelled projects can be deleted")
    db.delete(project)
    db.commit()


@router.delete("/{project_id}/invoice", status_code=204)
def delete_invoice(project_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """Delete (soft) the invoice linked to a project and reset the project back to invoiceable state."""
    from app.modules.finance.models import Invoice as InvModel
    project = ctrl.get_project(db, project_id)
    if not project.invoice_id:
        raise HTTPException(404, "No invoice for this project")
    inv = db.query(InvModel).filter_by(id=project.invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if float(inv.paid_amount or 0) > 0:
        raise HTTPException(400, "Cannot delete a partially or fully paid invoice")
    inv.deleted_at = datetime.utcnow()
    project.invoice_id = None
    # Revert status: go back to br_received if skip_br was used, else completed
    from app.modules.service_projects.models import ServiceProjectStatus
    project.status = ServiceProjectStatus.br_received if project.skip_br else ServiceProjectStatus.completed
    project.invoiced_at = None
    db.commit()


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
