"""
app/modules/service_projects/models.py
Service Projects (IT & Security) — DB models

v2 additions (requires migration.sql):
  ServiceType     : +code, +unit
  ServiceProject  : +project_number, +apply_tva, +skip_br_approved_by,
                    +created_by, +proposal/signed/bl/br/invoiced_at
  ServiceMilestone: +title, +service_type_id, +line_total
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, ForeignKey,
    DateTime, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ServiceCategory(str, enum.Enum):
    it_infrastructure = "it_infrastructure"
    network           = "network"
    security          = "security"
    solar             = "solar"
    cctv              = "cctv"
    access_control    = "access_control"
    maintenance       = "maintenance"
    other             = "other"


class ServiceProjectStatus(str, enum.Enum):
    draft         = "draft"
    proposal_sent = "proposal_sent"
    signed        = "signed"
    in_progress   = "in_progress"
    completed     = "completed"
    bl_sent       = "bl_sent"
    br_received   = "br_received"
    invoiced      = "invoiced"
    invoice_sent  = "invoice_sent"   # invoice sent, awaiting payment
    delivered     = "delivered"
    cancelled     = "cancelled"


class ServiceType(Base):
    __tablename__ = "service_types"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(40),  nullable=False, default="", index=True)  # NEW
    name        = Column(String(120), nullable=False)
    unit        = Column(String(50),  nullable=False, default="forfait")       # NEW
    category    = Column(SAEnum(ServiceCategory), nullable=False, default=ServiceCategory.other)
    description = Column(Text, nullable=True)
    unit_price  = Column(Numeric(14, 2), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    milestones  = relationship("ServiceMilestone", back_populates="service_type")


class ServiceProject(Base):
    __tablename__ = "service_projects"

    id              = Column(Integer, primary_key=True, index=True)
    reference       = Column(String(60), unique=True, nullable=False, index=True)
    project_number  = Column(String(60), nullable=True, index=True)            # NEW (= reference)
    title           = Column(String(200), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=True)
    category        = Column(SAEnum(ServiceCategory), nullable=False, default=ServiceCategory.other)
    status          = Column(SAEnum(ServiceProjectStatus), nullable=False,
                             default=ServiceProjectStatus.draft)

    site_address = Column(String(300), nullable=True)
    start_date   = Column(DateTime, nullable=True)
    end_date     = Column(DateTime, nullable=True)
    technician   = Column(String(120), nullable=True)

    currency        = Column(String(10), nullable=False, default="XAF")
    subtotal        = Column(Numeric(14, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(14, 2), default=0, nullable=False)
    tax_amount      = Column(Numeric(14, 2), default=0, nullable=False)   # TVA (added)
    retenue_amount  = Column(Numeric(14, 2), default=0, nullable=False)   # retenue à la source
    total           = Column(Numeric(14, 2), default=0, nullable=False)   # net à payer
    include_tax     = Column(Boolean, default=False, nullable=False)  # legacy
    apply_tva       = Column(Boolean, default=False, nullable=False)  # legacy canonical (→ tax_type)
    # Tax configuration (one tax type at a time)
    tax_type        = Column(String(20), nullable=False, default="none")  # none | tva | retenue
    tax_rate        = Column(Numeric(6, 3), default=0, nullable=False)     # percent, e.g. 19.250
    price_inclusive = Column(Boolean, default=False, nullable=False)       # entered prices are TTC
    # Fulfilment track — independent of billing status & payment
    delivered       = Column(Boolean, default=False, nullable=False)
    delivered_at    = Column(DateTime, nullable=True)

    skip_br             = Column(Boolean, default=False, nullable=False)
    skip_br_reason      = Column(Text, nullable=True)
    skip_br_approved_by = Column(Integer, nullable=True)                       # NEW

    invoice_id    = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    notes         = Column(Text, nullable=True)
    cancel_reason = Column(Text, nullable=True)
    created_by    = Column(Integer, nullable=True)                             # NEW

    # Workflow timestamps                                                       # NEW
    proposal_sent_at = Column(DateTime, nullable=True)
    signed_at        = Column(DateTime, nullable=True)
    bl_sent_at       = Column(DateTime, nullable=True)
    br_received_at   = Column(DateTime, nullable=True)
    invoiced_at      = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer     = relationship("Customer", backref="service_projects")
    service_type = relationship("ServiceType", foreign_keys=[service_type_id])
    milestones   = relationship("ServiceMilestone", back_populates="project",
                                cascade="all, delete-orphan",
                                order_by="ServiceMilestone.sort_order")
    invoice = relationship("Invoice", foreign_keys=[invoice_id])


class ServiceMilestone(Base):
    __tablename__ = "service_milestones"

    id               = Column(Integer, primary_key=True, index=True)
    project_id       = Column(Integer, ForeignKey("service_projects.id", ondelete="CASCADE"),
                              nullable=False)
    service_type_id  = Column(Integer, ForeignKey("service_types.id"), nullable=True)  # NEW
    title            = Column(String(200), nullable=True)                               # NEW
    description      = Column(String(300), nullable=True)   # kept for back-compat
    quantity         = Column(Numeric(10, 3), default=1,  nullable=False)
    unit_price       = Column(Numeric(14, 2), default=0,  nullable=False)
    total            = Column(Numeric(14, 2), default=0,  nullable=False)   # legacy
    line_total       = Column(Numeric(14, 2), default=0,  nullable=False)   # NEW canonical
    serials          = Column(Text, nullable=True)   # IMEI / SN / MAC, one per line
    progress         = Column(Integer, default=0,  nullable=False)
    sort_order       = Column(Integer, default=0,  nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                              nullable=False)

    project      = relationship("ServiceProject",  back_populates="milestones")
    service_type = relationship("ServiceType",     back_populates="milestones")
