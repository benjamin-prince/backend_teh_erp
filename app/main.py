"""
TEHTEK ERP — FastAPI Entry Point
URL: https://api2.tehtek.com/api/v1/...

Startup order:
  1. Create all DB tables (create_all)
  2. seed_sequences (MUST be first — everything else calls next_sequence)
  3. seed_parent_company
  4. seed_superadmin

Public whitelist (ACC-008):
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  POST /api/v1/auth/password-reset/request
  POST /api/v1/auth/password-reset/confirm
  GET  /api/v1/health
  GET  /api/v1/tracking/{tracking_number}
"""
import logging
from contextlib import asynccontextmanager
from app.modules.service_projects.models import (  # noqa: F401
    ServiceType, ServiceProject, ServiceMilestone
)
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine

from app.modules.companies.models import (  # noqa: F401
    SequenceRegistry, Company, Branch, Department, Team,
    PermissionFlag, ApprovalWorkflow
)
from app.modules.users.models import (  # noqa: F401
    Permission, Role, RolePermission, User, UserRole,
    PermissionFlagUser, RefreshToken, UserAuditLog
)
from app.modules.customers.models import (  # noqa: F401
    Customer, CustomerKYC, CustomerContact, CustomerNote, Supplier, SupplierContact
)
from app.modules.cargo.models import (  # noqa: F401
    Shipment, TrackingEvent, Bag, CarrierAssignment, PickupRequest
)
from app.modules.stock.models import (  # noqa: F401
    Product, Warehouse, StockItem, StockMovement, Reservation
)
from app.modules.orders.models import (  # noqa: F401
    Order, OrderItem, Exception_
)
from app.modules.infrastructure_services.models import (  # noqa: F401
    ServiceTicket, ServiceContract, ClientAsset, WarrantyRecord,
    SolarProject, MaintenanceSchedule
)
from app.modules.commissions.models import (  # noqa: F401
    CommissionPartner, Commission, CommissionPayout, CommissionDispute
)
from app.modules.finance.models import (  # noqa: F401
    Invoice, Payment, CashSession, Expense, Debt, DebtPayment
)
from app.modules.insurance.models import (  # noqa: F401
    InsurancePlan, InsurancePolicy, InsuranceClaim
)
from app.modules.finance.extended_models import Location, MoneyAccount, IncomeRecord, FinanceExpense, Receivable, BudgetLine

from app.modules.companies.router import router as companies_router
from app.modules.users.router import auth_router, protected_auth_router, users_router, roles_router
from app.modules.customers.router import router as customers_router
from app.modules.cargo.router import router as cargo_router
from app.modules.stock.router import router as stock_router
from app.modules.orders.router import router as orders_router
from app.modules.infrastructure_services.router import router as infra_router
from app.modules.commissions.router import router as commissions_router
from app.modules.finance.router import router as finance_router
from app.modules.insurance.router import router as insurance_router
from app.modules.containers.router import router as containers_router  # ← NEW
from app.modules.service_projects.router import router as service_projects_router
from app.modules.service_projects.service_types_router import router as service_types_router
from app.modules.finance.extended_router import router as finance_extended_router
from app.modules.personal.router import router as personal_router  # ← NEW

logger = logging.getLogger("tehtek")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TEHTEK ERP startup...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        from app.modules.companies.seeds import run_all_seeds
        run_all_seeds(db)
        from app.modules.users.controller import seed_superadmin
        company = db.query(Company).filter_by(code="TEHTEK").first()
        if company:
            created = seed_superadmin(db, company.id)
            if created:
                logger.info(f"FIRST LAUNCH: superadmin created — email={settings.SUPERADMIN_EMAIL}")
            else:
                logger.info("Superadmin already exists — skipped.")
        from app.modules.insurance.seeds import seed_insurance_plans
        if company:
            seed_insurance_plans(db, company.id)
        logger.info("Seeds complete.")
    except Exception as e:
        logger.error(f"Seed error: {e}")
        raise
    finally:
        db.close()
    logger.info("TEHTEK ERP ready at /api/v1/")
    yield
    logger.info("TEHTEK ERP shutting down.")


app = FastAPI(
    title="TEHTEK ERP API",
    description="TEHTEK IT Services — Cargo, Retail, Infrastructure",
    version="1.3.0",
    docs_url="/api/docs", # if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.get("/api/v1/health", tags=["system"])
def health():
    return {"status": "ok", "service": "TEHTEK ERP API"}


@app.get("/api/v1/tracking/{tracking_number}", tags=["tracking"])
def public_tracking(tracking_number: str):
    """Customer-facing tracking. No auth required. Returns public events only."""
    db = SessionLocal()
    try:
        shipment = db.query(Shipment).filter_by(tracking_number=tracking_number).first()
        if not shipment:
            raise HTTPException(404, "Tracking number not found")
        public_events = (
            db.query(TrackingEvent)
            .filter_by(shipment_id=shipment.id, is_public=True)
            .order_by(TrackingEvent.created_at.asc())
            .all()
        )
        return {
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "route": shipment.route,
            "shipment_type": shipment.shipment_type,
            "priority": shipment.priority,
            "sender_name": shipment.sender_name,
            "sender_country": shipment.sender_country,
            "receiver_name": shipment.receiver_name,
            "receiver_phone": shipment.receiver_phone,
            "receiver_country": shipment.receiver_country,
            "receiver_address": shipment.receiver_address,
            "weight_kg": float(shipment.weight_kg) if shipment.weight_kg is not None else None,
            "content_description": shipment.content_description,
            "delivery_type": shipment.delivery_type,
            "created_at": shipment.created_at.isoformat(),
            "events": [
                {
                    "event_type": e.event_type,
                    "description": e.description,
                    "location": e.location,
                    "timestamp": e.created_at.isoformat(),
                    "photos": e.photos or [],
                }
                for e in public_events
            ],
        }
    finally:
        db.close()


app.include_router(auth_router)
app.include_router(protected_auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(companies_router)
app.include_router(customers_router)
app.include_router(cargo_router)
app.include_router(stock_router)
app.include_router(orders_router)
app.include_router(infra_router)
app.include_router(commissions_router)
app.include_router(finance_extended_router)
app.include_router(finance_router)
app.include_router(insurance_router)
app.include_router(containers_router)  # ← ADD THIS
app.include_router(service_projects_router)
app.include_router(service_types_router)
app.include_router(personal_router)
