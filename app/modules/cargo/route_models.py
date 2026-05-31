"""TEHTEK — Cargo Route Models.

A CargoRoute is an admin-defined route (e.g. "Fret Maritime USA→CMR") that
carries an ordered list of CargoRouteStop records.  Each stop references a
Location (from finance.locations) and declares the tracking event_type that
gets recorded when a shipment reaches that stop.

The Shipment model stores cargo_route_id (nullable).  When set, the detail
page drives the stepper and checkpoint dropdown from the route's stops instead
of the old hardcoded WORKFLOW_SEQUENCE.

Stop visibility rules (condition column):
  NULL                       — always shown
  pickup_request             — only when shipment.pickup_type = "pickup_request"
  warehouse_dropoff          — only when shipment.pickup_type = "warehouse_dropoff"
  door_delivery              — only when shipment.delivery_type = "door_delivery"
  warehouse_or_agency_pickup — when delivery_type = "warehouse_pickup" OR "agency_pickup"
"""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class CargoRoute(Base):
    __tablename__ = "cargo_routes"

    id             = Column(Integer, primary_key=True)
    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name           = Column(String(150), nullable=False)   # "Fret Maritime USA → CMR"
    code           = Column(String(50),  nullable=False)   # "USA_CMR_SEA"
    origin_country = Column(String(100), nullable=False)   # "United States"
    dest_country   = Column(String(100), nullable=False)   # "Cameroon"
    transport_mode = Column(String(20),  nullable=False)   # sea / air / land / local
    is_active      = Column(Boolean, nullable=False, default=True)
    notes          = Column(Text, nullable=True)

    # Direct departure / arrival locations (replaces the multi-stop editor)
    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    dest_location_id   = Column(Integer, ForeignKey("locations.id"), nullable=True)

    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime, nullable=False, default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    stops = relationship(
        "CargoRouteStop",
        order_by="CargoRouteStop.sequence_order",
        back_populates="route",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    origin_location = relationship("Location", foreign_keys=[origin_location_id], lazy="joined")
    dest_location   = relationship("Location", foreign_keys=[dest_location_id],   lazy="joined")

    # Shipments that use this route (informational — no cascade delete)
    shipments = relationship("Shipment", back_populates="cargo_route", lazy="dynamic")


class CargoRouteStop(Base):
    __tablename__ = "cargo_route_stops"

    id             = Column(Integer, primary_key=True)
    route_id       = Column(Integer, ForeignKey("cargo_routes.id", ondelete="CASCADE"),
                            nullable=False)
    sequence_order = Column(Integer, nullable=False)

    # Physical location — nullable for virtual stops (e.g. "In Transit / Atlantique")
    location_id    = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Matches the frontend WORKFLOW_SEQUENCE event_type values:
    #   picked_up | warehouse_received | processed | departed | in_transit |
    #   arrived_destination | customs_cleared | out_for_delivery | delivered |
    #   ready_for_pickup | picked_up_by_receiver
    event_type     = Column(String(50), nullable=False)

    # Optional label override (if None, frontend uses the default event label)
    label          = Column(String(150), nullable=True)

    # Which side of the journey this stop belongs to — drives location filtering
    stop_side      = Column(String(20), nullable=False, default="origin")  # origin|transit|destination

    # Conditional visibility (see module docstring)
    condition      = Column(String(50), nullable=True)

    route    = relationship("CargoRoute", back_populates="stops")
    location = relationship("Location", lazy="joined")
