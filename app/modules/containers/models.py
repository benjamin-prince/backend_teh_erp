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

CONTAINER_TO_SHIPMENT_STATUS: dict[ContainerStatus, str] = {
    ContainerStatus.preparing:  "confirmed",
    ContainerStatus.loading:    "warehoused",
    ContainerStatus.loaded:     "warehoused",
    ContainerStatus.in_transit: "in_transit",
    ContainerStatus.arrived:    "in_transit",
    ContainerStatus.closed:     "delivered",
}

CONTAINER_TO_TRACKING_EVENT: dict[ContainerStatus, str] = {
    ContainerStatus.preparing:  "processed",
    ContainerStatus.loading:    "warehouse_received",
    ContainerStatus.loaded:     "processed",
    ContainerStatus.in_transit: "in_transit",
    ContainerStatus.arrived:    "arrived_destination",
    ContainerStatus.closed:     "delivered",
}

REQUIRES_TRACKING: set[ContainerStatus] = {
    ContainerStatus.loading,
    ContainerStatus.loaded,
    ContainerStatus.in_transit,
    ContainerStatus.arrived,
    ContainerStatus.closed,
}

REQUIRES_INVOICE: set[ContainerStatus] = {
    ContainerStatus.in_transit,
    ContainerStatus.arrived,
    ContainerStatus.closed,
}


class ShippingLine(Base):
    __tablename__ = "shipping_lines"

    id         = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    name                 = Column(String(255), nullable=False)
    code                 = Column(String(64),  nullable=True)   # e.g. MSCU, MAEU, CMDU
    phone                = Column(String(128), nullable=True)
    email                = Column(String(255), nullable=True)
    website              = Column(String(512), nullable=True)
    tracking_url_template = Column(String(512), nullable=True)  # {bl} placeholder
    notes                = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Broker(Base):
    __tablename__ = "brokers"

    id         = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    name         = Column(String(255), nullable=False)   # contact person / display name
    company_name = Column(String(255), nullable=True)    # brokerage firm name
    phone        = Column(String(128), nullable=True)
    email        = Column(String(255), nullable=True)
    notes        = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Container(Base):
    __tablename__ = "containers"

    id         = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id  = Column(BigInteger, ForeignKey("branches.id"),  nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"),     nullable=True)

    # ── Three distinct identifiers ────────────────────────────────────────────
    container_number = Column(String(64),  nullable=False, unique=True, index=True)
    tracking_number  = Column(String(128), nullable=True, index=True)
    invoice_number   = Column(String(128), nullable=True, index=True)

    # ── Shipping line (owner) — FK + denormalized name ────────────────────────
    shipping_line_id = Column(BigInteger, ForeignKey("shipping_lines.id"), nullable=True)
    owner_company    = Column(String(255), nullable=True)  # denormalized for display

    # ── Tracking link ─────────────────────────────────────────────────────────
    tracking_link = Column(String(512), nullable=True)

    # ── Broker — FK + denormalized fields ─────────────────────────────────────
    broker_id        = Column(BigInteger, ForeignKey("brokers.id"), nullable=True)
    broker_name      = Column(String(255), nullable=True)   # denormalized
    broker_company   = Column(String(255), nullable=True)   # denormalized
    broker_contact   = Column(String(128), nullable=True)   # phone, denormalized
    broker_reference = Column(String(128), nullable=True)   # broker's own file number

    # ── Core ──────────────────────────────────────────────────────────────────
    type   = Column(Enum(ContainerType),   nullable=False, default=ContainerType.sea)
    status = Column(Enum(ContainerStatus), nullable=False, default=ContainerStatus.preparing)

    cargo_route_id = Column(Integer, ForeignKey("cargo_routes.id"), nullable=True)

    depart_from    = Column(String(255), nullable=True)
    destination    = Column(String(255), nullable=True)
    load_date      = Column(Date, nullable=True)
    departure_date = Column(Date, nullable=True)
    arrival_date   = Column(Date, nullable=True)

    # ── Finance ───────────────────────────────────────────────────────────────
    total_spent      = Column(Numeric(18, 2), nullable=False, default=0)
    total_earned     = Column(Numeric(18, 2), nullable=False, default=0)
    currency         = Column(String(8),      nullable=False, default="XAF")
    packages_count   = Column(Integer,        nullable=False, default=0)
    customers_count  = Column(Integer,        nullable=False, default=0)

    notes     = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    shipping_line  = relationship("ShippingLine", foreign_keys=[shipping_line_id])
    broker         = relationship("Broker",        foreign_keys=[broker_id])
    cargo_route    = relationship("CargoRoute",    foreign_keys=[cargo_route_id], lazy="joined")
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
