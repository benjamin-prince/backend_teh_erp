"""TEHTEK — Rentals Module Models (équipements, véhicules, espaces)."""
from datetime import datetime
from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class RentalAsset(Base):
    """
    Anything TEHTEK rents out. Can point at a fleet vehicle (autopark)
    or stand alone (generator, space, tool…).
    """
    __tablename__ = "rental_assets"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name            = Column(String(150), nullable=False)
    asset_type      = Column(String(30), nullable=False, default="equipment")
    # vehicle | equipment | space | other
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=True)  # autopark link
    description     = Column(Text, nullable=True)

    # Rates (any subset may be set)
    rate_hourly     = Column(Numeric(14, 2), nullable=True)
    rate_daily      = Column(Numeric(14, 2), nullable=True)
    rate_weekly     = Column(Numeric(14, 2), nullable=True)
    rate_monthly    = Column(Numeric(14, 2), nullable=True)
    currency        = Column(String(10), default="XAF")
    deposit_amount  = Column(Numeric(14, 2), default=0)          # suggested caution

    status          = Column(String(30), default="available", nullable=False)
    # available | rented | maintenance | retired

    location_id     = Column(Integer, ForeignKey("locations.id"), nullable=True)
    photo_url       = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    contracts = relationship("RentalContract", back_populates="asset", lazy="select")

    __table_args__ = (
        Index("ix_rental_asset_company", "company_id"),
        Index("ix_rental_asset_status", "status"),
    )


class RentalContract(Base):
    """One rental agreement: asset × renter × period × rate."""
    __tablename__ = "rental_contracts"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    asset_id        = Column(Integer, ForeignKey("rental_assets.id"), nullable=False)

    contract_number = Column(String(30), unique=True, nullable=False)   # RNT-2026-07-000001

    # Renter: registered customer OR walk-in free text
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)
    renter_name     = Column(String(150), nullable=True)
    renter_phone    = Column(String(40), nullable=True)

    rate_period     = Column(String(10), nullable=False, default="day")
    # hour | day | week | month
    rate_amount     = Column(Numeric(14, 2), nullable=False)
    currency        = Column(String(10), default="XAF")

    start_date        = Column(Date, nullable=False)
    expected_end_date = Column(Date, nullable=True)
    actual_end_date   = Column(Date, nullable=True)

    total_amount    = Column(Numeric(14, 2), default=0)          # agreed / recalculated total
    amount_paid     = Column(Numeric(14, 2), default=0)

    deposit_amount          = Column(Numeric(14, 2), default=0)
    deposit_status          = Column(String(20), default="none")
    # none | held | returned | partial | withheld
    deposit_returned_amount = Column(Numeric(14, 2), nullable=True)

    status          = Column(String(20), default="active", nullable=False)
    # active | completed | cancelled          (overdue derived: active + expected_end < today)

    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset    = relationship("RentalAsset", back_populates="contracts")
    payments = relationship("RentalPayment", back_populates="contract", lazy="select")

    __table_args__ = (
        Index("ix_rental_contract_company", "company_id"),
        Index("ix_rental_contract_asset", "asset_id"),
        Index("ix_rental_contract_status", "status"),
    )


class RentalPayment(Base):
    """A payment received against a rental contract."""
    __tablename__ = "rental_payments"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contract_id     = Column(Integer, ForeignKey("rental_contracts.id"), nullable=False)

    amount          = Column(Numeric(14, 2), nullable=False)
    currency        = Column(String(10), default="XAF")
    payment_date    = Column(Date, nullable=False)
    payment_method  = Column(String(30), default="cash")
    # cash | mobile_money | bank_transfer | card | other
    reference       = Column(String(100), nullable=True)
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    contract = relationship("RentalContract", back_populates="payments")

    __table_args__ = (
        Index("ix_rental_payment_contract", "contract_id"),
    )
