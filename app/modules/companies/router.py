"""
TEHTEK — Companies Router
ACC-007: All routes protected. Auth applied at router level via dependencies.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.companies import controller, schemas
from app.modules.companies.models import (
    Company, Branch, Department, Team, ApprovalWorkflow
)

# ── ACC-007: Auth on every route in this router ───────────────────────────────
router = APIRouter(
    prefix="/api/v1",
    tags=["companies"],
    dependencies=[Depends(get_current_user)],
)


# ── Sequences ─────────────────────────────────────────────────────────────────

@router.get("/sequences", response_model=list[schemas.SequenceOut])
def list_sequences(db: Session = Depends(get_db)):
    from app.modules.companies.models import SequenceRegistry
    return db.query(SequenceRegistry).all()


# ── Companies ─────────────────────────────────────────────────────────────────

@router.post("/companies", response_model=schemas.CompanyOut, status_code=201)
def create_company(
    body: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    return controller.create_company(db, body.model_dump(), current_user.id)


@router.get("/companies", response_model=list[schemas.CompanyOut])
def list_companies(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return controller.list_companies(db, skip, limit)


@router.get("/companies/{company_id}", response_model=schemas.CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = controller.get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


@router.patch("/companies/{company_id}", response_model=schemas.CompanyOut)
def update_company(
    company_id: int,
    body: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    c = controller.get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return controller.update_company(db, c, body.model_dump(exclude_none=True))


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    c = controller.get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    controller.soft_delete_company(db, c)


# ── Branches ──────────────────────────────────────────────────────────────────

@router.post("/branches", response_model=schemas.BranchOut, status_code=201)
def create_branch(
    body: schemas.BranchCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    return controller.create_branch(db, body.model_dump(), current_user.id)


@router.get("/companies/{company_id}/branches", response_model=list[schemas.BranchOut])
def list_branches(company_id: int, db: Session = Depends(get_db)):
    return controller.list_branches(db, company_id)


@router.get("/branches/{branch_id}", response_model=schemas.BranchOut)
def get_branch(branch_id: int, db: Session = Depends(get_db)):
    b = controller.get_branch(db, branch_id)
    if not b:
        raise HTTPException(404, "Branch not found")
    return b


# ── Departments ───────────────────────────────────────────────────────────────

@router.post("/departments", response_model=schemas.DepartmentOut, status_code=201)
def create_department(
    body: schemas.DepartmentCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("settings:manage")),
):
    return controller.create_department(db, body.model_dump())


@router.get("/companies/{company_id}/departments", response_model=list[schemas.DepartmentOut])
def list_departments(company_id: int, db: Session = Depends(get_db)):
    return controller.list_departments(db, company_id)


# ── Teams ─────────────────────────────────────────────────────────────────────

@router.post("/teams", response_model=schemas.TeamOut, status_code=201)
def create_team(
    body: schemas.TeamCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("settings:manage")),
):
    return controller.create_team(db, body.model_dump())


# ── Approvals ─────────────────────────────────────────────────────────────────

@router.post("/approvals", response_model=schemas.ApprovalOut, status_code=201)
def create_approval(
    body: schemas.ApprovalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = body.model_dump()
    data["requested_by"] = current_user.id
    return controller.create_approval(db, data)


@router.get("/approvals", response_model=list[schemas.ApprovalOut])
def list_approvals(
    status: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("approvals:read")),
):
    q = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.company_id == current_user.company_id
    )
    if status:
        q = q.filter(ApprovalWorkflow.status == status)
    return q.all()


@router.get("/approvals/{approval_id}", response_model=schemas.ApprovalOut)
def get_approval(approval_id: int, db: Session = Depends(get_db)):
    a = db.query(ApprovalWorkflow).filter_by(id=approval_id).first()
    if not a:
        raise HTTPException(404, "Approval not found")
    return a


@router.post("/approvals/{approval_id}/decide", response_model=schemas.ApprovalOut)
def decide_approval(
    approval_id: int,
    body: schemas.ApprovalDecide,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("approvals:approve")),
):
    a = db.query(ApprovalWorkflow).filter_by(id=approval_id).first()
    if not a:
        raise HTTPException(404, "Approval not found")
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be 'approved' or 'rejected'")
    return controller.decide_approval(db, a, body.decision, current_user.id, body.reason)


@router.post("/approvals/{approval_id}/escalate", response_model=schemas.ApprovalOut)
def escalate_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("approvals:approve")),
):
    a = db.query(ApprovalWorkflow).filter_by(id=approval_id).first()
    if not a:
        raise HTTPException(404, "Approval not found")
    return controller.escalate_approval(db, a)
