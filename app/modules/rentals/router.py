"""TEHTEK — Rentals Router. ACC-007: auth at router level."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.rentals.models import RentalAsset, RentalContract, RentalPayment
from app.modules.autopark.models import Vehicle
from app.modules.companies.controller import next_sequence
from app.core.enums import SequenceType

router = APIRouter(
    prefix="/api/v1/rentals",
    tags=["rentals"],
    dependencies=[Depends(get_current_user)],
)

RATE_PERIODS = ("hour", "day", "week", "month")


# ── Schemas ───────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    name: str
    asset_type: str = "equipment"       # vehicle | equipment | space | other
    vehicle_id: Optional[int] = None
    description: Optional[str] = None
    rate_hourly: Optional[float] = None
    rate_daily: Optional[float] = None
    rate_weekly: Optional[float] = None
    rate_monthly: Optional[float] = None
    currency: str = "XAF"
    deposit_amount: float = 0
    status: str = "available"
    location_id: Optional[int] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    vehicle_id: Optional[int] = None
    description: Optional[str] = None
    rate_hourly: Optional[float] = None
    rate_daily: Optional[float] = None
    rate_weekly: Optional[float] = None
    rate_monthly: Optional[float] = None
    currency: Optional[str] = None
    deposit_amount: Optional[float] = None
    status: Optional[str] = None
    location_id: Optional[int] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None

class ContractCreate(BaseModel):
    asset_id: int
    customer_id: Optional[int] = None
    renter_name: Optional[str] = None
    renter_phone: Optional[str] = None
    rate_period: str = "day"
    rate_amount: float
    currency: str = "XAF"
    start_date: date
    expected_end_date: Optional[date] = None
    total_amount: float = 0
    deposit_amount: float = 0
    notes: Optional[str] = None

class ContractUpdate(BaseModel):
    renter_name: Optional[str] = None
    renter_phone: Optional[str] = None
    rate_period: Optional[str] = None
    rate_amount: Optional[float] = None
    expected_end_date: Optional[date] = None
    total_amount: Optional[float] = None
    deposit_amount: Optional[float] = None
    notes: Optional[str] = None

class ContractReturn(BaseModel):
    actual_end_date: Optional[date] = None
    total_amount: Optional[float] = None          # final agreed total (optional adjust)
    deposit_status: str = "returned"              # returned | partial | withheld
    deposit_returned_amount: Optional[float] = None
    notes: Optional[str] = None

class PaymentCreate(BaseModel):
    contract_id: int
    amount: float
    currency: str = "XAF"
    payment_date: date
    payment_method: str = "cash"
    reference: Optional[str] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_asset(db: Session, company_id: int, asset_id: int) -> RentalAsset:
    a = db.query(RentalAsset).filter_by(
        id=asset_id, company_id=company_id, deleted_at=None
    ).first()
    if not a:
        raise HTTPException(404, "Asset not found")
    return a


def _get_contract(db: Session, company_id: int, contract_id: int) -> RentalContract:
    c = db.query(RentalContract).filter_by(id=contract_id, company_id=company_id).first()
    if not c:
        raise HTTPException(404, "Contract not found")
    return c


def _contract_out(c: RentalContract) -> dict:
    is_overdue = (
        c.status == "active"
        and c.expected_end_date is not None
        and c.expected_end_date < date.today()
    )
    return {
        "id": c.id,
        "contract_number": c.contract_number,
        "asset_id": c.asset_id,
        "asset_name": c.asset.name if c.asset else None,
        "asset_type": c.asset.asset_type if c.asset else None,
        "customer_id": c.customer_id,
        "renter_name": c.renter_name,
        "renter_phone": c.renter_phone,
        "rate_period": c.rate_period,
        "rate_amount": float(c.rate_amount),
        "currency": c.currency,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "expected_end_date": c.expected_end_date.isoformat() if c.expected_end_date else None,
        "actual_end_date": c.actual_end_date.isoformat() if c.actual_end_date else None,
        "total_amount": float(c.total_amount or 0),
        "amount_paid": float(c.amount_paid or 0),
        "balance": float(c.total_amount or 0) - float(c.amount_paid or 0),
        "deposit_amount": float(c.deposit_amount or 0),
        "deposit_status": c.deposit_status,
        "deposit_returned_amount": float(c.deposit_returned_amount) if c.deposit_returned_amount is not None else None,
        "status": c.status,
        "is_overdue": is_overdue,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cid = current_user.company_id
    today = date.today()
    month_start = today.replace(day=1)

    assets = db.query(RentalAsset).filter_by(company_id=cid, deleted_at=None).all()
    active_contracts = db.query(RentalContract).filter_by(company_id=cid, status="active").all()
    overdue = [c for c in active_contracts if c.expected_end_date and c.expected_end_date < today]

    income_month = db.query(func.coalesce(func.sum(RentalPayment.amount), 0)).filter(
        RentalPayment.company_id == cid,
        RentalPayment.payment_date >= month_start,
        RentalPayment.currency == "XAF",
    ).scalar()

    deposits_held = sum(
        float(c.deposit_amount or 0) for c in active_contracts if c.deposit_status == "held"
    )

    outstanding = sum(
        max(0.0, float(c.total_amount or 0) - float(c.amount_paid or 0))
        for c in active_contracts
    )

    return {
        "total_assets": len(assets),
        "available_assets": sum(1 for a in assets if a.status == "available"),
        "rented_assets": sum(1 for a in assets if a.status == "rented"),
        "active_contracts": len(active_contracts),
        "overdue_contracts": len(overdue),
        "income_month_xaf": float(income_month or 0),
        "deposits_held_xaf": deposits_held,
        "outstanding_xaf": outstanding,
    }


# ── Assets ────────────────────────────────────────────────────────────────────

@router.get("/assets")
def list_assets(
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(RentalAsset).filter(
        RentalAsset.company_id == current_user.company_id,
        RentalAsset.deleted_at.is_(None),
    )
    if status:
        q = q.filter(RentalAsset.status == status)
    if asset_type:
        q = q.filter(RentalAsset.asset_type == asset_type)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(RentalAsset.name.ilike(like), RentalAsset.description.ilike(like)))
    return q.order_by(RentalAsset.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/assets", status_code=201)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if body.vehicle_id:
        v = db.query(Vehicle).filter_by(
            id=body.vehicle_id, company_id=current_user.company_id, deleted_at=None
        ).first()
        if not v:
            raise HTTPException(404, "Vehicle not found")
    a = RentalAsset(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/assets/{asset_id}")
def update_asset(
    asset_id: int,
    body: AssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    a = _get_asset(db, current_user.company_id, asset_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    a.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return a


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("settings:manage")),
):
    a = _get_asset(db, current_user.company_id, asset_id)
    active = db.query(RentalContract).filter_by(asset_id=asset_id, status="active").count()
    if active:
        raise HTTPException(400, "Ce bien a un contrat de location actif")
    a.deleted_at = datetime.utcnow()
    db.commit()


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
def list_contracts(
    status: Optional[str] = None,
    asset_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(RentalContract).filter_by(company_id=current_user.company_id)
    if status:
        q = q.filter(RentalContract.status == status)
    if asset_id:
        q = q.filter(RentalContract.asset_id == asset_id)
    if customer_id:
        q = q.filter(RentalContract.customer_id == customer_id)
    rows = q.order_by(RentalContract.created_at.desc()).offset(skip).limit(limit).all()
    out = [_contract_out(c) for c in rows]
    if overdue_only:
        out = [c for c in out if c["is_overdue"]]
    return out


@router.post("/contracts", status_code=201)
def create_contract(
    body: ContractCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if body.rate_period not in RATE_PERIODS:
        raise HTTPException(400, f"rate_period must be one of {RATE_PERIODS}")
    if not body.customer_id and not (body.renter_name or "").strip():
        raise HTTPException(400, "Indiquez un client ou un nom de locataire")

    asset = _get_asset(db, current_user.company_id, body.asset_id)
    if asset.status == "rented":
        raise HTTPException(400, "Ce bien est déjà en location")
    if asset.status in ("maintenance", "retired"):
        raise HTTPException(400, f"Ce bien n'est pas disponible ({asset.status})")

    number = next_sequence(db, SequenceType.invoice_number)
    number = f"RNT-{number.split('-', 1)[1]}"

    c = RentalContract(
        company_id=current_user.company_id,
        contract_number=number,
        deposit_status="held" if body.deposit_amount > 0 else "none",
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(c)
    asset.status = "rented"
    asset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _contract_out(c)


@router.get("/contracts/{contract_id}")
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = _get_contract(db, current_user.company_id, contract_id)
    out = _contract_out(c)
    out["payments"] = [{
        "id": p.id,
        "amount": float(p.amount),
        "currency": p.currency,
        "payment_date": p.payment_date.isoformat(),
        "payment_method": p.payment_method,
        "reference": p.reference,
        "notes": p.notes,
    } for p in sorted(c.payments, key=lambda p: (p.payment_date, p.id), reverse=True)]
    return out


@router.patch("/contracts/{contract_id}")
def update_contract(
    contract_id: int,
    body: ContractUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = _get_contract(db, current_user.company_id, contract_id)
    if c.status != "active":
        raise HTTPException(400, "Seuls les contrats actifs peuvent être modifiés")
    data = body.model_dump(exclude_unset=True)
    if "rate_period" in data and data["rate_period"] not in RATE_PERIODS:
        raise HTTPException(400, f"rate_period must be one of {RATE_PERIODS}")
    for k, v in data.items():
        setattr(c, k, v)
    if "deposit_amount" in data and c.deposit_status == "none" and float(c.deposit_amount or 0) > 0:
        c.deposit_status = "held"
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _contract_out(c)


@router.post("/contracts/{contract_id}/return")
def return_contract(
    contract_id: int,
    body: ContractReturn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Close a rental: asset comes back, deposit is settled."""
    c = _get_contract(db, current_user.company_id, contract_id)
    if c.status != "active":
        raise HTTPException(400, "Seuls les contrats actifs peuvent être clôturés")
    if body.deposit_status not in ("returned", "partial", "withheld"):
        raise HTTPException(400, "deposit_status must be returned | partial | withheld")

    c.actual_end_date = body.actual_end_date or date.today()
    if body.total_amount is not None:
        c.total_amount = body.total_amount
    if float(c.deposit_amount or 0) > 0:
        c.deposit_status = body.deposit_status
        if body.deposit_status == "returned":
            c.deposit_returned_amount = c.deposit_amount
        elif body.deposit_status == "withheld":
            c.deposit_returned_amount = 0
        else:
            c.deposit_returned_amount = body.deposit_returned_amount or 0
    if body.notes:
        c.notes = f"{c.notes}\n{body.notes}" if c.notes else body.notes
    c.status = "completed"
    c.updated_at = datetime.utcnow()

    asset = db.query(RentalAsset).filter_by(id=c.asset_id).first()
    if asset and asset.status == "rented":
        asset.status = "available"
        asset.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(c)
    return _contract_out(c)


@router.post("/contracts/{contract_id}/cancel")
def cancel_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = _get_contract(db, current_user.company_id, contract_id)
    if c.status != "active":
        raise HTTPException(400, "Seuls les contrats actifs peuvent être annulés")
    c.status = "cancelled"
    if c.deposit_status == "held":
        c.deposit_status = "returned"
        c.deposit_returned_amount = c.deposit_amount
    c.updated_at = datetime.utcnow()

    asset = db.query(RentalAsset).filter_by(id=c.asset_id).first()
    if asset and asset.status == "rented":
        asset.status = "available"
        asset.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(c)
    return _contract_out(c)


# ── Payments ──────────────────────────────────────────────────────────────────

@router.get("/payments")
def list_payments(
    contract_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(RentalPayment).filter_by(company_id=current_user.company_id)
    if contract_id:
        q = q.filter(RentalPayment.contract_id == contract_id)
    return q.order_by(
        RentalPayment.payment_date.desc(), RentalPayment.id.desc()
    ).offset(skip).limit(limit).all()


@router.post("/payments", status_code=201)
def create_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = _get_contract(db, current_user.company_id, body.contract_id)
    if c.status == "cancelled":
        raise HTTPException(400, "Contrat annulé — paiement impossible")
    if body.amount <= 0:
        raise HTTPException(400, "Le montant doit être positif")

    p = RentalPayment(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(p)
    c.amount_paid = float(c.amount_paid or 0) + body.amount
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = db.query(RentalPayment).filter_by(
        id=payment_id, company_id=current_user.company_id
    ).first()
    if not p:
        raise HTTPException(404, "Payment not found")
    c = db.query(RentalContract).filter_by(id=p.contract_id).first()
    if c:
        c.amount_paid = max(0.0, float(c.amount_paid or 0) - float(p.amount))
        c.updated_at = datetime.utcnow()
    db.delete(p)
    db.commit()
