"""TEHTEK — Infrastructure Services Models. Rules: ISR-001 to ISR-010, ESR-001 to ESR-010."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    ServiceTicketStatus, ContractType, SolarProjectStatus,
    EnergySystemType, ProjectPriority, WarrantyStatus
)


class ServiceTicket(Base):
    __tablename__ = "service_tickets"

    id               = Column(Integer, primary_key=True)
    company_id       = Column(Integer, ForeignKey("companies.id"), nullable=False)
    ticket_number    = Column(String(30), unique=True, nullable=False)  # SVC-2026-000001
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)  # ISR-001
    service_type     = Column(String(100), nullable=False)
    priority         = Column(String(20), default=ProjectPriority.standard)
    status           = Column(String(30), default=ServiceTicketStatus.draft)

    title            = Column(String(300), nullable=False)
    description      = Column(Text, nullable=True)
    scheduled_date   = Column(DateTime, nullable=True)
    assigned_to      = Column(Integer, nullable=True)  # technician user_id

    # ISR-003: customer signature required before completed
    customer_acceptance_signed = Column(Boolean, default=False)
    # ISR-004: service report required before completed
    service_report   = Column(Text, nullable=True)

    # ISR-008: emergency gets priority fee
    priority_fee     = Column(Numeric(14, 2), nullable=True)
    priority_fee_waived = Column(Boolean, default=False)

    # ISR-005: invoice auto-generated on completion
    invoice_id       = Column(Integer, nullable=True)

    site_address     = Column(Text, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at       = Column(DateTime, nullable=True)

    client_assets    = relationship("ClientAsset", back_populates="service_ticket", lazy="select")
    __table_args__   = (Index("ix_ticket_company_status", "company_id", "status"),)


class ServiceContract(Base):
    __tablename__ = "service_contracts"

    id                = Column(Integer, primary_key=True)
    company_id        = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contract_number   = Column(String(30), unique=True, nullable=False)  # CNT-2026-000001
    customer_id       = Column(Integer, ForeignKey("customers.id"), nullable=False)
    contract_type     = Column(String(30), nullable=False)
    # ISR-009: SLA fields required for recurring contracts
    response_time_hours = Column(Integer, nullable=True)
    covered_services  = Column(Text, nullable=True)   # JSON list
    excluded_services = Column(Text, nullable=True)   # JSON list
    billing_cycle     = Column(String(30), nullable=True)
    start_date        = Column(DateTime, nullable=True)
    end_date          = Column(DateTime, nullable=True)
    value             = Column(Numeric(14, 2), nullable=True)
    is_active         = Column(Boolean, default=True)
    created_by        = Column(Integer, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at        = Column(DateTime, nullable=True)


class ClientAsset(Base):
    """ISR-006: all installed equipment documented before job close."""
    __tablename__ = "client_assets"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_ticket_id = Column(Integer, ForeignKey("service_tickets.id"), nullable=True)
    name            = Column(String(200), nullable=False)
    model           = Column(String(200), nullable=True)
    serial_number   = Column(String(100), nullable=True)
    installation_date = Column(DateTime, nullable=True)
    location        = Column(String(300), nullable=True)  # ISR-006: required
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    service_ticket  = relationship("ServiceTicket", back_populates="client_assets")
    warranty        = relationship("WarrantyRecord", back_populates="asset",
                                   uselist=False, lazy="select")


class WarrantyRecord(Base):
    """ISR-007: warranty on every installed device."""
    __tablename__ = "warranty_records"

    id               = Column(Integer, primary_key=True)
    asset_id         = Column(Integer, ForeignKey("client_assets.id"), nullable=False)
    status           = Column(String(30), default=WarrantyStatus.active)
    warranty_period_months = Column(Integer, nullable=False)
    warranty_start_date    = Column(DateTime, nullable=False)
    warranty_end_date      = Column(DateTime, nullable=False)
    terms            = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)

    asset = relationship("ClientAsset", back_populates="warranty")


class SolarProject(Base):
    """ESR-001 to ESR-010."""
    __tablename__ = "solar_projects"

    id               = Column(Integer, primary_key=True)
    company_id       = Column(Integer, ForeignKey("companies.id"), nullable=False)
    project_number   = Column(String(30), unique=True, nullable=False)  # PRJ-2026-000001
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status           = Column(String(30), default=SolarProjectStatus.lead)
    system_type      = Column(String(50), nullable=True)
    priority         = Column(String(20), default=ProjectPriority.standard)

    # ESR-001
    site_survey_completed = Column(Boolean, default=False)
    site_survey_report    = Column(Text, nullable=True)

    # ESR-002
    load_assessment_kwh         = Column(Numeric(10, 3), nullable=True)
    proposed_system_capacity_kwp = Column(Numeric(10, 3), nullable=True)

    # ESR-003
    customer_signed_quotation = Column(Boolean, default=False)
    deposit_paid              = Column(Boolean, default=False)
    deposit_amount            = Column(Numeric(14, 2), nullable=True)
    total_value               = Column(Numeric(14, 2), nullable=True)

    # ESR-007
    safety_checklist_completed = Column(Boolean, default=False)
    # ESR-008
    customer_final_acceptance  = Column(Boolean, default=False)
    # ESR-009
    supervisor_approved        = Column(Boolean, default=False)

    site_address     = Column(Text, nullable=True)
    commissioned_at  = Column(DateTime, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at       = Column(DateTime, nullable=True)

    __table_args__   = (Index("ix_solar_company_status", "company_id", "status"),)


class MaintenanceSchedule(Base):
    """ESR-005: auto-created on commissioning."""
    __tablename__ = "maintenance_schedules"

    id             = Column(Integer, primary_key=True)
    solar_project_id = Column(Integer, ForeignKey("solar_projects.id"), nullable=True)
    asset_id       = Column(Integer, ForeignKey("client_assets.id"), nullable=True)
    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    maintenance_type = Column(String(50), nullable=False)  # routine, annual, etc.
    status         = Column(String(30), default="scheduled")
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
