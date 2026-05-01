"""TEHTEK — Insurance Router. ACC-007: auth at router level."""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.insurance.models import InsurancePlan, InsurancePolicy, InsuranceClaim
from app.modules.companies.controller import next_sequence
from app.core.enums import SequenceType

router = APIRouter(
    prefix="/api/v1/insurance",
    tags=["insurance"],
    dependencies=[Depends(get_current_user)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    name_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    rate_pct: float
    min_premium: float = 0
    max_coverage: Optional[float] = None
    covers_loss: bool = True
    covers_damage: bool = False
    covers_theft: bool = False
    covers_delay: bool = False
    covers_customs: bool = False
    covers_all_risks: bool = False
    exclusions: Optional[str] = None
    exclusions_fr: Optional[str] = None
    sort_order: int = 0

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    name_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    rate_pct: Optional[float] = None
    min_premium: Optional[float] = None
    max_coverage: Optional[float] = None
    covers_loss: Optional[bool] = None
    covers_damage: Optional[bool] = None
    covers_theft: Optional[bool] = None
    covers_delay: Optional[bool] = None
    covers_customs: Optional[bool] = None
    covers_all_risks: Optional[bool] = None
    exclusions: Optional[str] = None
    exclusions_fr: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

class PolicyCreate(BaseModel):
    shipment_id: int
    customer_id: int
    plan_id: int
    insured_value: float
    notes: Optional[str] = None

class ClaimCreate(BaseModel):
    policy_id: int
    claim_type: str   # loss | damage | theft | delay | customs_seizure | other
    claimed_amount: float
    description: str
    evidence_urls: Optional[str] = None

class ClaimReview(BaseModel):
    decision: str    # approved | rejected
    approved_amount: Optional[float] = None
    review_notes: Optional[str] = None

class ClaimPay(BaseModel):
    payment_ref: Optional[str] = None


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Public endpoint — any logged-in user can see plans (for shipment creation)."""
    q = db.query(InsurancePlan).filter(
        InsurancePlan.company_id == current_user.company_id,
        InsurancePlan.deleted_at.is_(None),
    )
    if active_only:
        q = q.filter(InsurancePlan.is_active == True)
    return q.order_by(InsurancePlan.sort_order).all()


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(InsurancePlan).filter_by(id=plan_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Plan not found")
    return p


@router.post("/plans", status_code=201)
def create_plan(
    body: PlanCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    plan = InsurancePlan(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("settings:manage")),
):
    plan = db.query(InsurancePlan).filter_by(id=plan_id, deleted_at=None).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(plan, k, v)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("settings:manage")),
):
    plan = db.query(InsurancePlan).filter_by(id=plan_id, deleted_at=None).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.deleted_at = datetime.utcnow()
    db.commit()


# ── Premium Calculator ────────────────────────────────────────────────────────

@router.get("/calculate-premium")
def calculate_premium(
    plan_id: int,
    insured_value: float,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Calculate premium before creating a policy."""
    plan = db.query(InsurancePlan).filter_by(id=plan_id, deleted_at=None).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    raw_premium = float(plan.rate_pct) / 100 * insured_value
    premium = max(raw_premium, float(plan.min_premium))
    if plan.max_coverage and insured_value > float(plan.max_coverage):
        insured_value = float(plan.max_coverage)

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "insured_value": insured_value,
        "rate_pct": float(plan.rate_pct),
        "raw_premium": round(raw_premium, 2),
        "premium_amount": round(premium, 2),
        "currency": "XAF",
        "max_coverage": float(plan.max_coverage) if plan.max_coverage else None,
    }


# ── Policies ──────────────────────────────────────────────────────────────────

@router.post("/policies", status_code=201)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    plan = db.query(InsurancePlan).filter_by(id=body.plan_id, deleted_at=None).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not plan.is_active:
        raise HTTPException(400, "This plan is no longer available")

    # Calculate premium
    raw_premium = float(plan.rate_pct) / 100 * body.insured_value
    premium = max(raw_premium, float(plan.min_premium))

    # Check no existing active policy for same shipment
    existing = db.query(InsurancePolicy).filter_by(
        shipment_id=body.shipment_id,
        status="active",
    ).first()
    if existing:
        raise HTTPException(400, "This shipment already has an active insurance policy")

    policy_number = next_sequence(db, SequenceType.invoice_number)
    policy_number = f"INS-{policy_number.split('-', 1)[1]}"  # INS-2026-04-000001

    policy = InsurancePolicy(
        company_id=current_user.company_id,
        shipment_id=body.shipment_id,
        customer_id=body.customer_id,
        plan_id=body.plan_id,
        policy_number=policy_number,
        insured_value=body.insured_value,
        premium_amount=round(premium, 2),
        notes=body.notes,
        start_date=datetime.utcnow(),
        created_by=current_user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies")
def list_policies(
    shipment_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    q = db.query(InsurancePolicy).filter_by(company_id=current_user.company_id)
    if shipment_id:
        q = q.filter(InsurancePolicy.shipment_id == shipment_id)
    if customer_id:
        q = q.filter(InsurancePolicy.customer_id == customer_id)
    if status:
        q = q.filter(InsurancePolicy.status == status)
    return q.order_by(InsurancePolicy.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    p = db.query(InsurancePolicy).filter_by(id=policy_id).first()
    if not p:
        raise HTTPException(404, "Policy not found")
    return p


@router.post("/policies/{policy_id}/cancel")
def cancel_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("finance:cancel_invoice")),
):
    p = db.query(InsurancePolicy).filter_by(id=policy_id).first()
    if not p:
        raise HTTPException(404, "Policy not found")
    if p.status != "active":
        raise HTTPException(400, "Only active policies can be cancelled")
    p.status = "cancelled"
    p.updated_at = datetime.utcnow()
    db.commit()
    return p


# ── Claims ────────────────────────────────────────────────────────────────────

@router.post("/claims", status_code=201)
def file_claim(
    body: ClaimCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    policy = db.query(InsurancePolicy).filter_by(id=body.policy_id).first()
    if not policy:
        raise HTTPException(404, "Policy not found")
    if policy.status not in ("active", "claimed"):
        raise HTTPException(400, f"Policy status '{policy.status}' does not allow claims")
    if body.claimed_amount > float(policy.insured_value):
        raise HTTPException(400, f"Claimed amount cannot exceed insured value ({policy.insured_value} XAF)")

    claim_number = next_sequence(db, SequenceType.invoice_number)
    claim_number = f"CLM-{claim_number.split('-', 1)[1]}"

    claim = InsuranceClaim(
        company_id=current_user.company_id,
        policy_id=body.policy_id,
        customer_id=policy.customer_id,
        claim_number=claim_number,
        claim_type=body.claim_type,
        claimed_amount=body.claimed_amount,
        description=body.description,
        evidence_urls=body.evidence_urls,
        created_by=current_user.id,
    )
    db.add(claim)

    # Update policy status
    policy.status = "claimed"
    policy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(claim)
    return claim


@router.get("/claims")
def list_claims(
    policy_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    q = db.query(InsuranceClaim).filter_by(company_id=current_user.company_id)
    if policy_id:
        q = q.filter(InsuranceClaim.policy_id == policy_id)
    if status:
        q = q.filter(InsuranceClaim.status == status)
    return q.order_by(InsuranceClaim.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/claims/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(InsuranceClaim).filter_by(id=claim_id).first()
    if not c:
        raise HTTPException(404, "Claim not found")
    return c


@router.post("/claims/{claim_id}/review")
def review_claim(
    claim_id: int,
    body: ClaimReview,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:invoices")),
):
    claim = db.query(InsuranceClaim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.status != "open":
        raise HTTPException(400, "Claim is not in 'open' status")
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be 'approved' or 'rejected'")

    claim.status = body.decision
    claim.reviewed_by = current_user.id
    claim.review_notes = body.review_notes
    claim.reviewed_at = datetime.utcnow()
    if body.decision == "approved":
        claim.approved_amount = body.approved_amount or claim.claimed_amount
        # Update policy status
        db.query(InsurancePolicy).filter_by(id=claim.policy_id).update({"status": "claim_pending"})
    else:
        db.query(InsurancePolicy).filter_by(id=claim.policy_id).update({"status": "claim_rejected"})
    claim.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/claims/{claim_id}/pay")
def mark_claim_paid(
    claim_id: int,
    body: ClaimPay,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:payments")),
):
    claim = db.query(InsuranceClaim).filter_by(id=claim_id).first()
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.status != "approved":
        raise HTTPException(400, "Claim must be approved before marking as paid")

    claim.status = "paid"
    claim.paid_at = datetime.utcnow()
    claim.payment_ref = body.payment_ref
    claim.updated_at = datetime.utcnow()

    db.query(InsurancePolicy).filter_by(id=claim.policy_id).update({"status": "claim_paid"})
    db.commit()
    db.refresh(claim)
    return claim
