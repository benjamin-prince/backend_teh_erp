"""TEHTEK — Insurance Module Models."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class InsurancePlan(Base):
    """
    Insurance plan types offered by TEHTEK.
    Each plan has a rate (% of insured value) and defined coverage.
    """
    __tablename__ = "insurance_plans"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name            = Column(String(100), nullable=False)       # e.g. "Basic", "Standard", "Premium"
    name_fr         = Column(String(100), nullable=True)        # French name
    description     = Column(Text, nullable=True)
    description_fr  = Column(Text, nullable=True)

    # Rate applied to insured_value to calculate premium
    rate_pct        = Column(Numeric(5, 3), nullable=False)     # e.g. 2.500 = 2.5%
    min_premium     = Column(Numeric(14, 2), default=0)         # minimum charge in XAF
    max_coverage    = Column(Numeric(14, 2), nullable=True)     # max payout cap (null = unlimited)

    # What is covered (stored as comma-separated keys)
    covers_loss         = Column(Boolean, default=True)
    covers_damage       = Column(Boolean, default=False)
    covers_theft        = Column(Boolean, default=False)
    covers_delay        = Column(Boolean, default=False)
    covers_customs      = Column(Boolean, default=False)        # customs seizure
    covers_all_risks    = Column(Boolean, default=False)        # all-in

    # Exclusions text
    exclusions      = Column(Text, nullable=True)
    exclusions_fr   = Column(Text, nullable=True)

    is_active       = Column(Boolean, default=True)
    sort_order      = Column(Integer, default=0)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    policies = relationship("InsurancePolicy", back_populates="plan", lazy="select")

    __table_args__ = (
        Index("ix_insurance_plan_company", "company_id"),
    )


class InsurancePolicy(Base):
    """
    One policy per shipment. Created when customer selects a plan.
    """
    __tablename__ = "insurance_policies"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    shipment_id     = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)
    plan_id         = Column(Integer, ForeignKey("insurance_plans.id"), nullable=False)

    policy_number   = Column(String(30), unique=True, nullable=False)  # INS-2026-000001
    status          = Column(String(30), default="active", nullable=False)
    # active | expired | claimed | cancelled | claim_paid | claim_rejected

    insured_value   = Column(Numeric(14, 2), nullable=False)    # declared by customer
    premium_amount  = Column(Numeric(14, 2), nullable=False)    # calculated: rate * insured_value
    currency        = Column(String(10), default="XAF")

    invoice_id      = Column(Integer, nullable=True)            # linked to finance invoice
    paid_at         = Column(DateTime, nullable=True)

    start_date      = Column(DateTime, nullable=False)
    end_date        = Column(DateTime, nullable=True)           # null = until delivery

    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan     = relationship("InsurancePlan", back_populates="policies")
    claims   = relationship("InsuranceClaim", back_populates="policy", lazy="select")

    __table_args__ = (
        Index("ix_policy_shipment", "shipment_id"),
        Index("ix_policy_customer", "customer_id"),
    )


class InsuranceClaim(Base):
    """
    Filed when a covered event occurs (loss, damage, theft, etc.)
    """
    __tablename__ = "insurance_claims"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    policy_id       = Column(Integer, ForeignKey("insurance_policies.id"), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)

    claim_number    = Column(String(30), unique=True, nullable=False)  # CLM-2026-000001
    claim_type      = Column(String(30), nullable=False)
    # loss | damage | theft | delay | customs_seizure | other

    status          = Column(String(30), default="open", nullable=False)
    # open | under_review | approved | rejected | paid | closed

    claimed_amount  = Column(Numeric(14, 2), nullable=False)    # what customer claims
    approved_amount = Column(Numeric(14, 2), nullable=True)     # what we approve

    description     = Column(Text, nullable=False)              # what happened
    evidence_urls   = Column(Text, nullable=True)               # comma-separated photo/doc links

    reviewed_by     = Column(Integer, nullable=True)
    review_notes    = Column(Text, nullable=True)
    reviewed_at     = Column(DateTime, nullable=True)

    paid_at         = Column(DateTime, nullable=True)
    payment_ref     = Column(String(200), nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = relationship("InsurancePolicy", back_populates="claims")

    __table_args__ = (
        Index("ix_claim_policy", "policy_id"),
        Index("ix_claim_status", "status"),
    )
