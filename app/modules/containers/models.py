# app/modules/containers/models.py

from __future__ import annotations

import enum

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ContainerType(str, enum.Enum):
    sea      = "sea"
    air      = "air"
    groupage = "groupage"


class ContainerStatus(str, enum.Enum):
    preparing  = "preparing"   # no requirements
    loading    = "loading"     # requires container.tracking_number
    loaded     = "loaded"      # requires container.tracking_number
    in_transit = "in_transit"  # requires container.tracking_number + invoice_number
    arrived    = "arrived"     # requires container.tracking_number + invoice_number
    closed     = "closed"      # requires container.tracking_number + invoice_number


# ── Cascade maps ───────────────────────────────────────────────────────────────

# When container status changes, cascade this status to all loaded shipments
CONTAINER_TO_SHIPMENT_STATUS: dict[ContainerStatus, str] = {
    ContainerStatus.preparing:  "confirmed",
    ContainerStatus.loading:    "warehoused",
    ContainerStatus.loaded:     "warehoused",
    ContainerStatus.in_transit: "in_transit",
    ContainerStatus.arrived:    "in_transit",
    ContainerStatus.closed:     "delivered",
}

# When container status changes, add this tracking event to all loaded shipments
CONTAINER_TO_TRACKING_EVENT: dict[ContainerStatus, str] = {
    ContainerStatus.preparing:  "processed",
    ContainerStatus.loading:    "warehouse_received",
    ContainerStatus.loaded:     "processed",
    ContainerStatus.in_transit: "in_transit",
    ContainerStatus.arrived:    "arrived_destination",
    ContainerStatus.closed:     "delivered",
}

# Container must have tracking_number before moving to these statuses
REQUIRES_TRACKING: set[ContainerStatus] = {
    ContainerStatus.loading,
    ContainerStatus.loaded,
    ContainerStatus.in_transit,
    ContainerStatus.arrived,
    ContainerStatus.closed,
}

# Container must ALSO have invoice_number before moving to these statuses
REQUIRES_INVOICE: set[ContainerStatus] = {
    ContainerStatus.in_transit,
    ContainerStatus.arrived,
    ContainerStatus.closed,
}


class Container(Base):
    __tablename__ = "containers"

    id         = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id  = Column(BigInteger, ForeignKey("branches.id"),  nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"),     nullable=True)

    # ── Three distinct identifiers ────────────────────────────────────────────
    container_number = Column(String(64),  nullable=False, unique=True, index=True)
    # ^ Internal sequential ref, auto-generated: CONT-2026-0001, AIR-2026-0001, GRP-2026-0001

    tracking_number  = Column(String(128), nullable=True, index=True)
    # ^ Carrier BL / AWB number entered manually — required for loading+

    invoice_number   = Column(String(128), nullable=True, index=True)
    # ^ Commercial invoice number — required for in_transit+

    # ── Owner ─────────────────────────────────────────────────────────────────
    owner_name    = Column(String(255), nullable=True)
    owner_company = Column(String(255), nullable=True)
    owner_contact = Column(String(128), nullable=True)

    # ── Tracking link ─────────────────────────────────────────────────────────
    tracking_link = Column(String(512), nullable=True)  # public carrier URL

    # ── Broker / freight forwarder ────────────────────────────────────────────
    broker_name      = Column(String(255), nullable=True)
    broker_company   = Column(String(255), nullable=True)
    broker_contact   = Column(String(128), nullable=True)
    broker_reference = Column(String(128), nullable=True)  # broker's own file number

    # ── Core ──────────────────────────────────────────────────────────────────
    type   = Column(Enum(ContainerType),   nullable=False, default=ContainerType.sea)
    status = Column(Enum(ContainerStatus), nullable=False, default=ContainerStatus.preparing)

    depart_from    = Column(String(255), nullable=True)
    destination    = Column(String(255), nullable=True)
    load_date      = Column(Date, nullable=True)
    departure_date = Column(Date, nullable=True)
    arrival_date   = Column(Date, nullable=True)

    # ── Finance ───────────────────────────────────────────────────────────────
    total_spent      = Column(Numeric(18, 2), nullable=False, default=0)
    total_earned     = Column(Numeric(18, 2), nullable=False, default=0)
    currency         = Column(String(8),      nullable=False, default="XAF")
    packages_count   = Column(Integer,        nullable=False, default=0)  # denormalized
    customers_count  = Column(Integer,        nullable=False, default=0)  # denormalized

    notes     = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    shipment_links = relationship(
        "ContainerShipment",
        back_populates="container",
        cascade="all, delete-orphan",
    )


class ContainerShipment(Base):
    __tablename__ = "container_shipments"

    id           = Column(BigInteger, primary_key=True, index=True)
    container_id = Column(BigInteger, ForeignKey("containers.id", ondelete="CASCADE"), nullable=False, index=True)
    shipment_id  = Column(BigInteger, ForeignKey("shipments.id",  ondelete="CASCADE"), nullable=False, index=True)
    added_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    added_by     = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    container = relationship("Container", back_populates="shipment_links")
    shipment  = relationship("Shipment")
