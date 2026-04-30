"""TEHTEK — Infrastructure Services Router. ACC-007: auth at router level."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.infrastructure_services.models import (
    ServiceTicket, ServiceContract, ClientAsset, WarrantyRecord,
    SolarProject, MaintenanceSchedule
)
from app.modules.companies.controller import next_sequence
from app.core.enums import ServiceTicketStatus, SolarProjectStatus, SequenceType

router = APIRouter(
    prefix="/api/v1",
    tags=["infrastructure"],
    dependencies=[Depends(get_current_user)],
)


# ── Inline schemas ────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    customer_id: int
    service_type: str
    title: str
    description: Optional[str] = None
    priority: str = "standard"
    site_address: Optional[str] = None

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    service_report: Optional[str] = None
    customer_acceptance_signed: Optional[bool] = None
    priority_fee: Optional[float] = None
    assigned_to: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None

class ContractCreate(BaseModel):
    customer_id: int
    contract_type: str
    response_time_hours: Optional[int] = None
    covered_services: Optional[str] = None
    billing_cycle: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    value: Optional[float] = None

class AssetCreate(BaseModel):
    customer_id: int
    service_ticket_id: Optional[int] = None
    name: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[datetime] = None
    location: Optional[str] = None

class WarrantyCreate(BaseModel):
    warranty_period_months: int
    warranty_start_date: datetime
    terms: Optional[str] = None

class SolarCreate(BaseModel):
    customer_id: int
    system_type: Optional[str] = None
    priority: str = "standard"
    site_address: Optional[str] = None
    total_value: Optional[float] = None

class SolarUpdate(BaseModel):
    status: Optional[str] = None
    site_survey_completed: Optional[bool] = None
    site_survey_report: Optional[str] = None
    load_assessment_kwh: Optional[float] = None
    proposed_system_capacity_kwp: Optional[float] = None
    customer_signed_quotation: Optional[bool] = None
    deposit_paid: Optional[bool] = None
    deposit_amount: Optional[float] = None
    safety_checklist_completed: Optional[bool] = None
    customer_final_acceptance: Optional[bool] = None
    supervisor_approved: Optional[bool] = None
    notes: Optional[str] = None


# ── Service Tickets ───────────────────────────────────────────────────────────

@router.post("/service-tickets", status_code=201)
def create_ticket(
    body: TicketCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:create")),
):
    number = next_sequence(db, SequenceType.service_ticket)
    ticket = ServiceTicket(
        company_id=current_user.company_id,
        ticket_number=number,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/service-tickets")
def list_tickets(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:read")),
):
    q = db.query(ServiceTicket).filter(
        ServiceTicket.company_id == current_user.company_id,
        ServiceTicket.deleted_at.is_(None),
    )
    if status:
        q = q.filter(ServiceTicket.status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/service-tickets/{ticket_id}")
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("it_services:read")),
):
    t = db.query(ServiceTicket).filter_by(id=ticket_id, deleted_at=None).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


@router.patch("/service-tickets/{ticket_id}")
def update_ticket(
    ticket_id: int,
    body: TicketUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:update")),
):
    t = db.query(ServiceTicket).filter_by(id=ticket_id, deleted_at=None).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    # ISR-003 + ISR-004: cannot mark completed without both checks
    if body.status == ServiceTicketStatus.completed:
        if not t.customer_acceptance_signed:
            raise HTTPException(400, "Customer acceptance signature required before completion (ISR-003)")
        if not t.service_report:
            raise HTTPException(400, "Service report required before completion (ISR-004)")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    t.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    return t


# ── Service Contracts ─────────────────────────────────────────────────────────

@router.post("/service-contracts", status_code=201)
def create_contract(
    body: ContractCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:create")),
):
    number = next_sequence(db, SequenceType.contract_number)
    contract = ServiceContract(
        company_id=current_user.company_id,
        contract_number=number,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/service-contracts")
def list_contracts(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:read")),
):
    return db.query(ServiceContract).filter(
        ServiceContract.company_id == current_user.company_id,
        ServiceContract.deleted_at.is_(None),
    ).all()


# ── Client Assets ─────────────────────────────────────────────────────────────

@router.post("/client-assets", status_code=201)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:update")),
):
    """ISR-006: location required."""
    if not body.location:
        raise HTTPException(400, "Asset location is required (ISR-006)")
    asset = ClientAsset(
        company_id=current_user.company_id,
        **body.model_dump(),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/client-assets")
def list_assets(
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:read")),
):
    q = db.query(ClientAsset).filter_by(company_id=current_user.company_id)
    if customer_id:
        q = q.filter(ClientAsset.customer_id == customer_id)
    return q.all()


@router.post("/client-assets/{asset_id}/warranty", status_code=201)
def add_warranty(
    asset_id: int,
    body: WarrantyCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("it_services:update")),
):
    """ISR-007: warranty record on installed device."""
    from datetime import timedelta
    asset = db.query(ClientAsset).filter_by(id=asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    end_date = body.warranty_start_date.replace(
        month=body.warranty_start_date.month + (body.warranty_period_months % 12),
        year=body.warranty_start_date.year + (body.warranty_period_months // 12),
    ) if body.warranty_period_months else body.warranty_start_date
    warranty = WarrantyRecord(
        asset_id=asset_id,
        warranty_end_date=end_date,
        **body.model_dump(),
    )
    db.add(warranty)
    db.commit()
    db.refresh(warranty)
    return warranty


# ── Solar Projects ────────────────────────────────────────────────────────────

@router.post("/solar-projects", status_code=201)
def create_solar_project(
    body: SolarCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("solar:create")),
):
    number = next_sequence(db, SequenceType.project_number)
    project = SolarProject(
        company_id=current_user.company_id,
        project_number=number,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/solar-projects")
def list_solar_projects(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("solar:read")),
):
    q = db.query(SolarProject).filter(
        SolarProject.company_id == current_user.company_id,
        SolarProject.deleted_at.is_(None),
    )
    if status:
        q = q.filter(SolarProject.status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/solar-projects/{project_id}")
def get_solar_project(
    project_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("solar:read")),
):
    p = db.query(SolarProject).filter_by(id=project_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Solar project not found")
    return p


@router.patch("/solar-projects/{project_id}")
def update_solar_project(
    project_id: int,
    body: SolarUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("solar:update")),
):
    p = db.query(SolarProject).filter_by(id=project_id, deleted_at=None).first()
    if not p:
        raise HTTPException(404, "Solar project not found")
    # ESR gate checks before commissioning
    if body.status == SolarProjectStatus.commissioned:
        if not p.safety_checklist_completed:
            raise HTTPException(400, "Safety checklist must be completed (ESR-007)")
        if not p.customer_final_acceptance:
            raise HTTPException(400, "Customer final acceptance required (ESR-008)")
        if not p.supervisor_approved:
            raise HTTPException(400, "Supervisor sign-off required (ESR-009)")
        p.commissioned_at = datetime.utcnow()
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p


# ── Maintenance Schedules ─────────────────────────────────────────────────────

@router.get("/maintenance-schedules")
def list_maintenance(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("it_services:read")),
):
    return db.query(MaintenanceSchedule).filter_by(
        company_id=current_user.company_id
    ).all()
