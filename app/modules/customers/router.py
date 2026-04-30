"""TEHTEK — Customers Router. ACC-007: auth at router level."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.customers import controller, schemas
from app.modules.customers.models import CustomerKYC

router = APIRouter(
    prefix="/api/v1",
    tags=["customers"],
    dependencies=[Depends(get_current_user)],
)

# ── Customers ─────────────────────────────────────────────────────────────────

@router.post("/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(
    body: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:create")),
):
    data = body.model_dump()
    if not current_user.is_superadmin:
        data["company_id"] = current_user.company_id
    return controller.create_customer(db, data, current_user.id)

@router.get("/customers", response_model=list[schemas.CustomerOut])
def list_customers(
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:read")),
):
    return controller.list_customers(db, current_user.company_id, skip, limit)

@router.get("/customers/by-code/{code}", response_model=schemas.CustomerOut)
def get_by_code(code: str, db: Session = Depends(get_db), _=Depends(require_permission("customers:read"))):
    c = controller.get_by_code(db, code)
    if not c:
        raise HTTPException(404, "Customer not found")
    return c

@router.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_permission("customers:read"))):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return c

@router.patch("/customers/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: int, body: schemas.CustomerUpdate,
    db: Session = Depends(get_db), _=Depends(require_permission("customers:update")),
):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.update_customer(db, c, body.model_dump(exclude_none=True))

@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int, db: Session = Depends(get_db),
    _=Depends(require_permission("customers:delete")),
):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    controller.soft_delete_customer(db, c)

@router.get("/customers/{customer_id}/validate")
def validate_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.validate_for_transaction(c)

@router.post("/customers/{customer_id}/blacklist", response_model=schemas.CustomerOut)
def blacklist(
    customer_id: int, body: schemas.BlacklistRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:blacklist")),
):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.blacklist_customer(db, c, body.reason, current_user.id)

@router.post("/customers/{customer_id}/remove-blacklist", response_model=schemas.CustomerOut)
def remove_blacklist(
    customer_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:blacklist")),
):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.remove_blacklist(db, c, current_user.id)

@router.post("/customers/{customer_id}/grant-vip", response_model=schemas.CustomerOut)
def grant_vip(
    customer_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:vip_grant")),
):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.grant_vip(db, c, current_user.id)

@router.post("/customers/{customer_id}/revoke-vip", response_model=schemas.CustomerOut)
def revoke_vip(customer_id: int, db: Session = Depends(get_db), _=Depends(require_permission("customers:vip_grant"))):
    c = controller.get_customer(db, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return controller.revoke_vip(db, c)

# ── KYC ──────────────────────────────────────────────────────────────────────

@router.post("/customers/{customer_id}/kyc", response_model=schemas.KYCOut, status_code=201)
def submit_kyc(customer_id: int, body: schemas.KYCSubmit, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return controller.submit_kyc(db, customer_id, body.model_dump())

@router.get("/customers/{customer_id}/kyc", response_model=list[schemas.KYCOut])
def get_kyc(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(CustomerKYC).filter_by(customer_id=customer_id).all()

@router.post("/kyc/{kyc_id}/review", response_model=schemas.KYCOut)
def review_kyc(
    kyc_id: int, body: schemas.KYCReview,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("customers:kyc_verify")),
):
    kyc = db.query(CustomerKYC).filter_by(id=kyc_id).first()
    if not kyc:
        raise HTTPException(404, "KYC record not found")
    return controller.review_kyc(db, kyc, body.decision, current_user.id, body.note)

# ── Contacts ──────────────────────────────────────────────────────────────────

@router.post("/customers/{customer_id}/contacts", response_model=schemas.ContactOut, status_code=201)
def add_contact(customer_id: int, body: schemas.ContactCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return controller.add_contact(db, customer_id, body.model_dump())

@router.get("/customers/{customer_id}/contacts", response_model=list[schemas.ContactOut])
def list_contacts(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.modules.customers.models import CustomerContact
    return db.query(CustomerContact).filter_by(customer_id=customer_id).all()

# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/customers/{customer_id}/notes", response_model=schemas.NoteOut, status_code=201)
def add_note(customer_id: int, body: schemas.NoteCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return controller.add_note(db, customer_id, body.content, current_user.id)

@router.get("/customers/{customer_id}/notes", response_model=list[schemas.NoteOut])
def list_notes(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.modules.customers.models import CustomerNote
    return db.query(CustomerNote).filter_by(customer_id=customer_id).all()

# ── Suppliers ─────────────────────────────────────────────────────────────────

@router.post("/suppliers", response_model=schemas.SupplierOut, status_code=201)
def create_supplier(
    body: schemas.SupplierCreate, db: Session = Depends(get_db),
    current_user=Depends(require_permission("procurement:create")),
):
    data = body.model_dump()
    if not current_user.is_superadmin:
        data["company_id"] = current_user.company_id
    return controller.create_supplier(db, data, current_user.id)

@router.get("/suppliers", response_model=list[schemas.SupplierOut])
def list_suppliers(db: Session = Depends(get_db), current_user=Depends(require_permission("procurement:read"))):
    return controller.list_suppliers(db, current_user.company_id)

@router.get("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _=Depends(require_permission("procurement:read"))):
    s = controller.get_supplier(db, supplier_id)
    if not s:
        raise HTTPException(404, "Supplier not found")
    return s
