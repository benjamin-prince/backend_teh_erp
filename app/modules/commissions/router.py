"""TEHTEK — Commissions Router. ACC-007: auth at router level."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.commissions.models import (
    CommissionPartner, Commission, CommissionPayout, CommissionDispute
)
from app.modules.companies.controller import next_sequence
from app.core.enums import (
    CommissionStatus, CommissionPayoutStatus, CommissionDisputeStatus, SequenceType
)

router = APIRouter(
    prefix="/api/v1/commissions",
    tags=["commissions"],
    dependencies=[Depends(get_current_user)],
)


class PartnerCreate(BaseModel):
    first_name: str
    last_name: str
    partner_type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    payment_method: Optional[str] = None
    mobile_money_number: Optional[str] = None
    default_rate_pct: Optional[float] = None
    flat_rate_xaf: Optional[float] = None

class CommissionCreate(BaseModel):
    partner_id: int
    commission_amount: float
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None
    ref_number: Optional[str] = None
    transaction_value: Optional[float] = None
    rate_pct: Optional[float] = None
    notes: Optional[str] = None

class PayoutCreate(BaseModel):
    partner_id: int
    commission_ids: list[int]
    payment_method: Optional[str] = None

class DisputeCreate(BaseModel):
    commission_id: int
    reason: str


# ── Partners ──────────────────────────────────────────────────────────────────

@router.post("/partners", status_code=201)
def create_partner(
    body: PartnerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:manage")),
):
    partner = CommissionPartner(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.get("/partners")
def list_partners(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:read")),
):
    return db.query(CommissionPartner).filter(
        CommissionPartner.company_id == current_user.company_id,
        CommissionPartner.deleted_at.is_(None),
    ).all()


@router.get("/partners/{partner_id}")
def get_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("commissions:read")),
):
    p = db.query(CommissionPartner).filter_by(id=partner_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Partner not found")
    return p


@router.post("/partners/{partner_id}/flag-fraud")
def flag_fraud(
    partner_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:manage")),
):
    p = db.query(CommissionPartner).filter_by(id=partner_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Partner not found")
    p.fraud_flagged = True
    p.fraud_flag_reason = reason
    db.commit()
    return {"flagged": True, "partner_id": partner_id}


# ── Commissions ───────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_commission(
    body: CommissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:manage")),
):
    number = next_sequence(db, SequenceType.commission_record)
    commission = Commission(
        company_id=current_user.company_id,
        commission_number=number,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(commission)
    db.commit()
    db.refresh(commission)
    return commission


@router.get("")
def list_commissions(
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:read")),
):
    q = db.query(Commission).filter_by(company_id=current_user.company_id)
    if partner_id:
        q = q.filter(Commission.partner_id == partner_id)
    if status:
        q = q.filter(Commission.status == status)
    return q.offset(skip).limit(limit).all()


# ── Payouts ───────────────────────────────────────────────────────────────────

@router.post("/payouts", status_code=201)
def create_payout(
    body: PayoutCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:manage")),
):
    """Batch commissions into a payout."""
    commissions = db.query(Commission).filter(
        Commission.id.in_(body.commission_ids),
        Commission.status == CommissionStatus.payable,
    ).all()
    if len(commissions) != len(body.commission_ids):
        raise HTTPException(400, "Some commissions are not in 'payable' status")

    total = sum(float(c.commission_amount) for c in commissions)
    payout_number = next_sequence(db, SequenceType.payout_number)
    payout = CommissionPayout(
        company_id=current_user.company_id,
        partner_id=body.partner_id,
        payout_number=payout_number,
        total_amount=total,
        payment_method=body.payment_method,
        requested_by=current_user.id,
    )
    db.add(payout)
    db.flush()

    for c in commissions:
        c.payout_id = payout.id
        c.status = CommissionStatus.paid
        c.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(payout)
    return payout


@router.get("/payouts")
def list_payouts(
    partner_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:read")),
):
    q = db.query(CommissionPayout).filter_by(company_id=current_user.company_id)
    if partner_id:
        q = q.filter(CommissionPayout.partner_id == partner_id)
    return q.all()


@router.post("/payouts/{payout_id}/approve")
def approve_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:approve")),
):
    payout = db.query(CommissionPayout).filter_by(id=payout_id).first()
    if not payout:
        raise HTTPException(404, "Payout not found")
    payout.status = CommissionPayoutStatus.approved
    payout.approved_by = current_user.id
    payout.approved_at = datetime.utcnow()
    db.commit()
    return payout


# ── Disputes ──────────────────────────────────────────────────────────────────

@router.post("/disputes", status_code=201)
def raise_dispute(
    body: DisputeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    dispute = CommissionDispute(
        company_id=current_user.company_id,
        partner_id=db.query(Commission).filter_by(id=body.commission_id).first().partner_id,
        **body.model_dump(),
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return dispute


@router.post("/disputes/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: int,
    decision: str,
    resolution: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("commissions:approve")),
):
    d = db.query(CommissionDispute).filter_by(id=dispute_id).first()
    if not d:
        raise HTTPException(404, "Dispute not found")
    d.status = decision
    d.resolution = resolution
    d.resolved_by = current_user.id
    d.resolved_at = datetime.utcnow()
    db.commit()
    return d
