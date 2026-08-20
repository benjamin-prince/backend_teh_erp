"""TEHTEK — Ad campaigns (Facebook & co) with spend + lead attribution.

Leads are attributed to a campaign by time window: every WhatsApp lead created
between start_date and end_date (or now, while the ad runs) counts for that ad.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text

from app.core.database import Base


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id         = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)

    name       = Column(String(200), nullable=False)
    platform   = Column(String(30), nullable=False, default="facebook")  # facebook | instagram | tiktok | google | other
    ad_url     = Column(Text, nullable=True)          # link to the post / ads-manager campaign

    budget     = Column(Numeric(14, 2), nullable=False, default=0)
    spend      = Column(Numeric(14, 2), nullable=False, default=0)
    currency   = Column(String(10), nullable=False, default="XAF")

    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date   = Column(DateTime, nullable=True)      # NULL = still running
    status     = Column(String(20), nullable=False, default="active")   # active | paused | ended

    notes      = Column(Text, nullable=True)

    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
