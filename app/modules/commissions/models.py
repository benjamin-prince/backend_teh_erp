"""TEHTEK — Commissions Module Models."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    CommissionPartnerType, CommissionPartnerStatus,
    CommissionStatus, CommissionPayoutStatus, CommissionDisputeStatus
)


class CommissionPartner(Base):
    __tablename__ = "commission_partners"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)
    partner_type    = Column(String(50), nullable=False)
    status          = Column(String(30), default=CommissionPartnerStatus.active)

    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    email           = Column(String(255), nullable=True)
    phone           = Column(String(30), nullable=True)

    # Payout details
    payment_method  = Column(String(30), nullable=True)
    mobile_money_number = Column(String(30), nullable=True)
    bank_name       = Column(String(100), nullable=True)
    bank_account    = Column(String(100), nullable=True)

    # Default commission rate
    default_rate_pct  = Column(Numeric(5, 2), nullable=True)   # e.g. 5.00 = 5%
    flat_rate_xaf     = Column(Numeric(14, 2), nullable=True)  # alternative flat fee

    total_earned    = Column(Numeric(14, 2), default=0)
    total_paid      = Column(Numeric(14, 2), default=0)
    total_pending   = Column(Numeric(14, 2), default=0)

    fraud_flagged   = Column(Boolean, default=False)
    fraud_flag_reason = Column(Text, nullable=True)

    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    commissions = relationship("Commission", back_populates="partner", lazy="select")
    __table_args__ = (Index("ix_partner_company", "company_id"),)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Commission(Base):
    """One record per earned commission event."""
    __tablename__ = "commissions"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    partner_id      = Column(Integer, ForeignKey("commission_partners.id"), nullable=False)
    commission_number = Column(String(30), unique=True, nullable=False)  # COM-2026-000001

    # What triggered this commission
    ref_model       = Column(String(50), nullable=True)   # "shipment", "order", "solar_project"
    ref_id          = Column(Integer, nullable=True)
    ref_number      = Column(String(50), nullable=True)   # tracking_number / order_number

    # Amount
    transaction_value = Column(Numeric(14, 2), nullable=True)
    rate_pct          = Column(Numeric(5, 2), nullable=True)
    commission_amount = Column(Numeric(14, 2), nullable=False)

    status          = Column(String(30), default=CommissionStatus.pending)
    payable_after   = Column(DateTime, nullable=True)   # waiting for payment clearance

    payout_id       = Column(Integer, ForeignKey("commission_payouts.id"), nullable=True)

    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    partner = relationship("CommissionPartner", back_populates="commissions")
    payout  = relationship("CommissionPayout", back_populates="commissions")
    __table_args__ = (Index("ix_commission_partner_status", "partner_id", "status"),)


class CommissionPayout(Base):
    """Batched payout to a partner."""
    __tablename__ = "commission_payouts"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    partner_id      = Column(Integer, ForeignKey("commission_partners.id"), nullable=False)
    payout_number   = Column(String(30), unique=True, nullable=False)  # PAY-2026-04-000001
    status          = Column(String(30), default=CommissionPayoutStatus.pending)

    total_amount    = Column(Numeric(14, 2), nullable=False)
    payment_method  = Column(String(30), nullable=True)
    payment_reference = Column(String(200), nullable=True)

    requested_by    = Column(Integer, nullable=True)
    approved_by     = Column(Integer, nullable=True)
    processed_by    = Column(Integer, nullable=True)
    approved_at     = Column(DateTime, nullable=True)
    processed_at    = Column(DateTime, nullable=True)

    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    commissions = relationship("Commission", back_populates="payout")


class CommissionDispute(Base):
    __tablename__ = "commission_disputes"

    id            = Column(Integer, primary_key=True)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)
    commission_id = Column(Integer, ForeignKey("commissions.id"), nullable=False)
    partner_id    = Column(Integer, ForeignKey("commission_partners.id"), nullable=False)
    status        = Column(String(30), default=CommissionDisputeStatus.open)
    reason        = Column(Text, nullable=False)
    resolution    = Column(Text, nullable=True)
    resolved_by   = Column(Integer, nullable=True)
    resolved_at   = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
