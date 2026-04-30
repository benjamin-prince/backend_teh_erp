"""TEHTEK — Cargo Module Models. Rules: SR-001 to SR-010, CB-001 to CB-004."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    ShipmentType, ShipmentRoute, ShipmentStatus, ShipmentPriority,
    PickupType, DeliveryType, PackageCondition, Incoterm,
    InsuranceStatus, CarrierType, CarrierStatus, BagType, BagStatus,
    TrackingEventType
)


class Shipment(Base):
    __tablename__ = "shipments"

    id                 = Column(Integer, primary_key=True)
    company_id         = Column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id          = Column(Integer, ForeignKey("branches.id"), nullable=True)
    tracking_number    = Column(String(50), unique=True, nullable=True)  # set on confirmation (SR-002)
    customer_id        = Column(Integer, ForeignKey("customers.id"), nullable=False)  # SR-001
    shipment_type      = Column(String(30), nullable=False)
    route              = Column(String(30), nullable=False)
    status             = Column(String(30), nullable=False, default=ShipmentStatus.draft)
    priority           = Column(String(20), default=ShipmentPriority.standard)

    # Origin / destination
    sender_name        = Column(String(200), nullable=True)
    sender_phone       = Column(String(30), nullable=True)
    sender_address     = Column(Text, nullable=True)
    sender_country     = Column(String(100), nullable=True)
    receiver_name      = Column(String(200), nullable=True)
    receiver_phone     = Column(String(30), nullable=True)
    receiver_address   = Column(Text, nullable=True)
    receiver_country   = Column(String(100), nullable=True)

    # Dimensions (SR-005)
    weight_kg          = Column(Numeric(10, 3), nullable=True)
    length_cm          = Column(Numeric(10, 2), nullable=True)
    width_cm           = Column(Numeric(10, 2), nullable=True)
    height_cm          = Column(Numeric(10, 2), nullable=True)

    # Customs (SR-007)
    declared_value     = Column(Numeric(14, 2), nullable=True)
    customs_value      = Column(Numeric(14, 2), nullable=True)
    customs_currency   = Column(String(10), default="XAF")
    incoterm           = Column(String(10), default=Incoterm.dap)
    content_description = Column(Text, nullable=True)

    # Insurance (SR-010)
    insurance_status   = Column(String(30), default=InsuranceStatus.not_requested)
    insured_value      = Column(Numeric(14, 2), nullable=True)

    # Declarations (SR-008, SR-009)
    declaration_accepted   = Column(Boolean, default=False)
    declaration_ip         = Column(String(45), nullable=True)
    declaration_at         = Column(DateTime, nullable=True)
    prohibited_check_done  = Column(Boolean, default=False)

    # Delivery
    delivery_type      = Column(String(30), default=DeliveryType.warehouse_pickup)
    pickup_type        = Column(String(30), default=PickupType.warehouse_dropoff)
    delivery_attempts  = Column(Integer, default=0)

    # Storage (ST-001, ST-002)
    arrived_at         = Column(DateTime, nullable=True)
    storage_start_date = Column(DateTime, nullable=True)
    storage_fee_per_day = Column(Numeric(10, 2), nullable=True)

    # Bag assignment
    bag_id             = Column(Integer, ForeignKey("bags.id"), nullable=True)

    photo_count        = Column(Integer, default=0)
    notes              = Column(Text, nullable=True)
    created_by         = Column(Integer, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at         = Column(DateTime, nullable=True)

    tracking_events = relationship("TrackingEvent", back_populates="shipment", lazy="select")
    bag             = relationship("Bag", back_populates="shipments")

    __table_args__ = (
        Index("ix_shipment_company_status", "company_id", "status"),
        Index("ix_shipment_tracking", "tracking_number"),
        Index("ix_shipment_customer", "customer_id"),
    )


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id           = Column(Integer, primary_key=True)
    shipment_id  = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    event_type   = Column(String(50), nullable=False)
    description  = Column(Text, nullable=True)
    location     = Column(String(200), nullable=True)
    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_public    = Column(Boolean, default=True)  # customer-visible

    shipment = relationship("Shipment", back_populates="tracking_events")


class Bag(Base):
    __tablename__ = "bags"

    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    bag_number  = Column(String(30), unique=True, nullable=False)  # BAG-AIR-2026-0012
    bag_type    = Column(String(30), nullable=False, default=BagType.bag)
    status      = Column(String(30), nullable=False, default=BagStatus.open)
    route       = Column(String(30), nullable=True)
    total_weight_kg = Column(Numeric(10, 3), default=0)
    package_count   = Column(Integer, default=0)
    sealed_at   = Column(DateTime, nullable=True)
    manifest_locked = Column(Boolean, default=False)  # CB-001
    notes       = Column(Text, nullable=True)
    created_by  = Column(Integer, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipments        = relationship("Shipment", back_populates="bag", lazy="select")
    carrier_assignment = relationship("CarrierAssignment", back_populates="bag",
                                      uselist=False, lazy="select")


class CarrierAssignment(Base):
    """CB-002: All fields required before assignment."""
    __tablename__ = "carrier_assignments"

    id           = Column(Integer, primary_key=True)
    bag_id       = Column(Integer, ForeignKey("bags.id"), nullable=False, unique=True)
    carrier_type = Column(String(30), nullable=False)
    status       = Column(String(30), nullable=False, default=CarrierStatus.available)
    # Traveler details (required for air_express)
    full_name    = Column(String(200), nullable=False)
    id_number    = Column(String(100), nullable=False)
    flight_number = Column(String(50), nullable=True)
    departure_date = Column(DateTime, nullable=True)
    destination  = Column(String(100), nullable=True)
    phone        = Column(String(30), nullable=False)
    max_weight_kg = Column(Numeric(10, 3), nullable=True)
    notes        = Column(Text, nullable=True)
    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    bag = relationship("Bag", back_populates="carrier_assignment")


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    pickup_number = Column(String(30), unique=True, nullable=False)  # PKP-2026-000001
    address     = Column(Text, nullable=False)
    city        = Column(String(100), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    assigned_to = Column(Integer, nullable=True)
    status      = Column(String(30), default="pending")
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
