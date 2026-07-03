"""TEHTEK — Auto-Parc (Fleet Management) Module Models."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Vehicle(Base):
    """
    A company vehicle — car, truck, van, motorbike, bus.
    Current assignment (site + driver) is denormalized here for fast lists;
    full history lives in VehicleAssignment.
    """
    __tablename__ = "vehicles"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name            = Column(String(120), nullable=False)       # e.g. "Hilux blanc chantier"
    vehicle_type    = Column(String(30), nullable=False, default="car")
    # car | truck | van | motorbike | bus | machine | other
    usage_type      = Column(String(20), nullable=False, default="business")
    # business | personal | rental | sale
    brand           = Column(String(60), nullable=True)          # Toyota
    model           = Column(String(60), nullable=True)          # Hilux
    year            = Column(Integer, nullable=True)
    color           = Column(String(40), nullable=True)
    registration_plate = Column(String(30), nullable=True)       # LT 1234 AB
    vin             = Column(String(60), nullable=True)          # chassis number

    fuel_type       = Column(String(20), default="essence")
    # essence | diesel | hybride | electrique | autre
    tank_capacity_l = Column(Numeric(6, 1), nullable=True)
    current_odometer_km = Column(Numeric(10, 1), default=0)

    status          = Column(String(30), default="active", nullable=False)
    # active | in_maintenance | out_of_service | sold

    purchase_date   = Column(Date, nullable=True)
    purchase_price  = Column(Numeric(14, 2), nullable=True)
    currency        = Column(String(10), default="XAF")

    # Current assignment (denormalized — see VehicleAssignment for history)
    assigned_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    assigned_driver_name  = Column(String(120), nullable=True)
    assigned_driver_phone = Column(String(40), nullable=True)

    photo_url       = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    fuel_logs    = relationship("FuelLog", back_populates="vehicle", lazy="select")
    maintenances = relationship("VehicleMaintenance", back_populates="vehicle", lazy="select")
    documents    = relationship("VehicleDocument", back_populates="vehicle", lazy="select")
    assignments  = relationship("VehicleAssignment", back_populates="vehicle", lazy="select")

    __table_args__ = (
        Index("ix_vehicle_company", "company_id"),
        Index("ix_vehicle_status", "status"),
    )


class FuelLog(Base):
    """One refuelling event. Consumption is derived between full-tank logs."""
    __tablename__ = "vehicle_fuel_logs"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    log_date        = Column(Date, nullable=False)
    odometer_km     = Column(Numeric(10, 1), nullable=True)
    liters          = Column(Numeric(8, 2), nullable=False)
    price_per_liter = Column(Numeric(10, 2), nullable=True)
    total_cost      = Column(Numeric(14, 2), nullable=False)
    currency        = Column(String(10), default="XAF")
    full_tank       = Column(Boolean, default=True)
    station         = Column(String(120), nullable=True)
    receipt_url     = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="fuel_logs")

    __table_args__ = (
        Index("ix_fuel_vehicle", "vehicle_id"),
        Index("ix_fuel_date", "log_date"),
    )


class VehicleMaintenance(Base):
    """Planned or completed maintenance / repair."""
    __tablename__ = "vehicle_maintenances"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    maintenance_type = Column(String(30), nullable=False, default="autre")
    # vidange | revision | reparation | pneus | freins | batterie | carrosserie | autre
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)

    status          = Column(String(20), default="planned", nullable=False)
    # planned | in_progress | done | cancelled

    scheduled_date  = Column(Date, nullable=True)
    completed_date  = Column(Date, nullable=True)
    odometer_km     = Column(Numeric(10, 1), nullable=True)
    cost            = Column(Numeric(14, 2), default=0)
    currency        = Column(String(10), default="XAF")
    garage_name     = Column(String(120), nullable=True)
    invoice_ref     = Column(String(100), nullable=True)

    # Next occurrence reminders (e.g. next vidange)
    next_due_date   = Column(Date, nullable=True)
    next_due_km     = Column(Numeric(10, 1), nullable=True)

    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="maintenances")

    __table_args__ = (
        Index("ix_maint_vehicle", "vehicle_id"),
        Index("ix_maint_status", "status"),
    )


class VehicleDocument(Base):
    """Administrative document with expiry — carte grise, assurance, vignette, visite technique."""
    __tablename__ = "vehicle_documents"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    doc_type        = Column(String(30), nullable=False)
    # carte_grise | assurance | vignette | visite_technique | autre
    reference       = Column(String(100), nullable=True)         # policy / doc number
    provider        = Column(String(120), nullable=True)         # insurer / issuer
    issue_date      = Column(Date, nullable=True)
    expiry_date     = Column(Date, nullable=True)
    cost            = Column(Numeric(14, 2), default=0)
    currency        = Column(String(10), default="XAF")
    file_url        = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    vehicle = relationship("Vehicle", back_populates="documents")

    __table_args__ = (
        Index("ix_vehdoc_vehicle", "vehicle_id"),
        Index("ix_vehdoc_expiry", "expiry_date"),
    )


class VehicleAssignment(Base):
    """Assignment history: which site / driver had the vehicle, and when."""
    __tablename__ = "vehicle_assignments"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    location_id     = Column(Integer, ForeignKey("locations.id"), nullable=True)
    driver_name     = Column(String(120), nullable=True)
    driver_phone    = Column(String(40), nullable=True)

    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=True)                # null = current
    notes           = Column(Text, nullable=True)

    created_by      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    vehicle = relationship("Vehicle", back_populates="assignments")

    __table_args__ = (
        Index("ix_vehassign_vehicle", "vehicle_id"),
    )
