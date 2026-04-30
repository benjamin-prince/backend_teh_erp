"""TEHTEK — Companies Controller"""
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.companies.models import (
    SequenceRegistry, Company, Branch, Department, Team,
    PermissionFlag, ApprovalWorkflow
)
from app.core.enums import ApprovalStatus, SequenceType


# ── Sequence Generator (SEQ-001) ─────────────────────────────────────────────

ROUTE_CODES = {
    "china_cameroon":  "CNACM",
    "usa_cameroon":    "USACM",
    "europe_cameroon": "EURCM",
    "cameroon_china":  "CMCNA",
    "cameroon_usa":    "CMUSA",
    "cameroon_local":  "CMLOC",
    "cameroon_africa": "CMAFR",
}


def next_sequence(db: Session, seq_type: str, route: Optional[str] = None) -> str:
    """
    SEQ-001: Atomic increment via SELECT FOR UPDATE.
    Returns a fully formatted sequence string.
    """
    row = (
        db.query(SequenceRegistry)
        .filter_by(sequence_type=seq_type)
        .with_for_update()
        .first()
    )
    if not row:
        raise ValueError(f"Sequence '{seq_type}' not found. Run seeds first.")

    row.current_value += 1
    row.updated_at = datetime.utcnow()
    db.flush()

    now = datetime.utcnow()
    val = str(row.current_value).zfill(row.pad_length)

    if seq_type == SequenceType.tracking_number:
        route_code = ROUTE_CODES.get(route or "", "UNK")
        return f"{row.prefix}-{route_code}-{now.year}-{val}"

    if row.month_scoped:
        return f"{row.prefix}-{now.year}-{now.month:02d}-{val}"

    if row.year_scoped:
        return f"{row.prefix}-{now.year}-{val}"

    # No date scope (e.g. customer_code CUS-000034)
    return f"{row.prefix}-{val}"


# ── Company CRUD ──────────────────────────────────────────────────────────────

def create_company(db: Session, data: dict, actor_id: int) -> Company:
    company = Company(**data, created_by=actor_id)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def list_companies(db: Session, skip: int = 0, limit: int = 50):
    return (
        db.query(Company)
        .filter(Company.deleted_at.is_(None))
        .offset(skip).limit(limit).all()
    )


def get_company(db: Session, company_id: int) -> Optional[Company]:
    return db.query(Company).filter(
        Company.id == company_id, Company.deleted_at.is_(None)
    ).first()


def update_company(db: Session, company: Company, data: dict) -> Company:
    for k, v in data.items():
        setattr(company, k, v)
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return company


def soft_delete_company(db: Session, company: Company) -> None:
    company.deleted_at = datetime.utcnow()
    db.commit()


# ── Branch CRUD ───────────────────────────────────────────────────────────────

def create_branch(db: Session, data: dict, actor_id: int) -> Branch:
    branch = Branch(**data, created_by=actor_id)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


def list_branches(db: Session, company_id: int):
    return db.query(Branch).filter(
        Branch.company_id == company_id, Branch.deleted_at.is_(None)
    ).all()


def get_branch(db: Session, branch_id: int) -> Optional[Branch]:
    return db.query(Branch).filter(
        Branch.id == branch_id, Branch.deleted_at.is_(None)
    ).first()


# ── Department CRUD ───────────────────────────────────────────────────────────

def create_department(db: Session, data: dict) -> Department:
    dept = Department(**data)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def list_departments(db: Session, company_id: int):
    return db.query(Department).filter(
        Department.company_id == company_id, Department.deleted_at.is_(None)
    ).all()


# ── Team CRUD ─────────────────────────────────────────────────────────────────

def create_team(db: Session, data: dict) -> Team:
    team = Team(**data)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


# ── Approval Workflow ─────────────────────────────────────────────────────────

def create_approval(db: Session, data: dict) -> ApprovalWorkflow:
    approval = ApprovalWorkflow(**data)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def decide_approval(
    db: Session,
    approval: ApprovalWorkflow,
    decision: str,   # "approved" | "rejected"
    actor_id: int,
    reason: str,
) -> ApprovalWorkflow:
    approval.status = decision
    approval.approved_by = actor_id
    approval.decision_reason = reason
    approval.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)
    return approval


def escalate_approval(db: Session, approval: ApprovalWorkflow) -> ApprovalWorkflow:
    approval.status = ApprovalStatus.escalated
    approval.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)
    return approval
