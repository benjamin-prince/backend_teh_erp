"""
Ads API — record posted campaigns, spend, and see leads/customers per ad.

  GET    /api/v1/ads               — list with per-ad stats (leads, converted, cost/lead)
  POST   /api/v1/ads               — create
  PATCH  /api/v1/ads/{id}          — update (incl. spend)
  DELETE /api/v1/ads/{id}          — soft delete
  GET    /api/v1/ads/{id}/leads    — leads attributed to this ad (time window)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.ads.models import AdCampaign
from app.modules.whatsapp.models import WhatsAppLead

router = APIRouter(
    prefix="/api/v1/ads",
    tags=["Ads"],
    dependencies=[Depends(get_current_user)],
)


class AdIn(BaseModel):
    name:       str
    platform:   str = "facebook"
    ad_url:     Optional[str] = None
    budget:     float = 0
    spend:      float = 0
    currency:   str = "XAF"
    start_date: Optional[str] = None   # ISO date (yyyy-mm-dd)
    end_date:   Optional[str] = None
    status:     str = "active"
    notes:      Optional[str] = None


class AdPatch(BaseModel):
    name:       Optional[str] = None
    platform:   Optional[str] = None
    ad_url:     Optional[str] = None
    budget:     Optional[float] = None
    spend:      Optional[float] = None
    currency:   Optional[str] = None
    start_date: Optional[str] = None
    end_date:   Optional[str] = None
    status:     Optional[str] = None
    notes:      Optional[str] = None


def _parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s[:19]) if "T" in s else datetime.fromisoformat(s + "T00:00:00")


def _window_query(db: Session, ad: AdCampaign):
    q = db.query(WhatsAppLead).filter(WhatsAppLead.created_at >= ad.start_date)
    if ad.end_date:
        q = q.filter(WhatsAppLead.created_at <= ad.end_date)
    return q


def _stats(db: Session, ad: AdCampaign) -> dict:
    q = _window_query(db, ad)
    leads = q.count()
    converted = q.filter(WhatsAppLead.status == "converted").count()
    spend = float(ad.spend or 0)
    return {
        "leads": leads,
        "converted": converted,
        "cost_per_lead": round(spend / leads, 2) if leads > 0 else None,
        "cost_per_customer": round(spend / converted, 2) if converted > 0 else None,
    }


def _out(ad: AdCampaign, db: Session) -> dict:
    d = {c.name: getattr(ad, c.name) for c in ad.__table__.columns}
    d.update(_stats(db, ad))
    return d


@router.get("")
def list_ads(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ads = (
        db.query(AdCampaign)
        .filter(AdCampaign.company_id == current_user.company_id, AdCampaign.deleted_at.is_(None))
        .order_by(AdCampaign.start_date.desc())
        .all()
    )
    return [_out(a, db) for a in ads]


@router.post("", status_code=201)
def create_ad(body: AdIn, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(400, "name is required")
    ad = AdCampaign(
        company_id=current_user.company_id,
        name=body.name.strip(),
        platform=body.platform,
        ad_url=body.ad_url,
        budget=body.budget,
        spend=body.spend,
        currency=body.currency,
        start_date=_parse(body.start_date) or datetime.utcnow(),
        end_date=_parse(body.end_date),
        status=body.status,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return _out(ad, db)


@router.patch("/{ad_id}")
def update_ad(ad_id: int, body: AdPatch, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ad = db.query(AdCampaign).filter_by(id=ad_id, company_id=current_user.company_id, deleted_at=None).first()
    if not ad:
        raise HTTPException(404, "Ad not found")
    data = body.model_dump(exclude_unset=True)
    for k in ("start_date", "end_date"):
        if k in data:
            data[k] = _parse(data[k])
    for k, v in data.items():
        setattr(ad, k, v)
    ad.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ad)
    return _out(ad, db)


@router.delete("/{ad_id}", status_code=204)
def delete_ad(ad_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ad = db.query(AdCampaign).filter_by(id=ad_id, company_id=current_user.company_id, deleted_at=None).first()
    if not ad:
        raise HTTPException(404, "Ad not found")
    ad.deleted_at = datetime.utcnow()
    db.commit()


@router.get("/{ad_id}/leads")
def ad_leads(ad_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ad = db.query(AdCampaign).filter_by(id=ad_id, company_id=current_user.company_id, deleted_at=None).first()
    if not ad:
        raise HTTPException(404, "Ad not found")
    rows = _window_query(db, ad).order_by(WhatsAppLead.created_at.desc()).limit(200).all()
    return [
        {
            "id": l.id, "name": l.name, "phone": l.phone, "status": l.status,
            "pickup_address": l.pickup_address, "destination": l.destination,
            "cargo_type": l.cargo_type, "shipping_mode": l.shipping_mode,
            "preferred_pickup_date": l.preferred_pickup_date,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]
