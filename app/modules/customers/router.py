# """TEHTEK — Customers Router. ACC-007: auth at router level."""
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session

# from app.core.database import get_db
# from app.core.dependencies import get_current_user, require_permission
# from app.modules.companies.models import Company
# from app.modules.customers import controller, schemas
# from app.modules.companies.models import Company
# from app.modules.customers.models import CustomerKYC

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["customers"],
#     dependencies=[Depends(get_current_user)],
# )

# # ── Customers ─────────────────────────────────────────────────────────────────

# @router.post("/customers", response_model=schemas.CustomerOut, status_code=201)
# def create_customer(
#     body: schemas.CustomerCreate,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:create")),
# ):
#     data = body.model_dump()
#     company_id = current_user.company_id
#     if not company_id:
#         company = db.query(Company).filter_by(code="TEHTEK").first()
#         if company:
#             company_id = company.id
#     data["company_id"] = company_id
#     return controller.create_customer(db, data, current_user.id)

# @router.get("/customers", response_model=list[schemas.CustomerOut])
# def list_customers(
#     skip: int = 0, limit: int = 50,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:read")),
# ):
#     return controller.list_customers(db, current_user.company_id, skip, limit)

# @router.get("/customers/by-code/{code}", response_model=schemas.CustomerOut)
# def get_by_code(code: str, db: Session = Depends(get_db), _=Depends(require_permission("customers:read"))):
#     c = controller.get_by_code(db, code)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return c

# @router.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
# def get_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_permission("customers:read"))):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return c

# @router.patch("/customers/{customer_id}", response_model=schemas.CustomerOut)
# def update_customer(
#     customer_id: int, body: schemas.CustomerUpdate,
#     db: Session = Depends(get_db), _=Depends(require_permission("customers:update")),
# ):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.update_customer(db, c, body.model_dump(exclude_none=True))

# @router.delete("/customers/{customer_id}", status_code=204)
# def delete_customer(
#     customer_id: int, db: Session = Depends(get_db),
#     _=Depends(require_permission("customers:delete")),
# ):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     controller.soft_delete_customer(db, c)

# @router.get("/customers/{customer_id}/validate")
# def validate_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.validate_for_transaction(c)

# @router.post("/customers/{customer_id}/blacklist", response_model=schemas.CustomerOut)
# def blacklist(
#     customer_id: int, body: schemas.BlacklistRequest,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:blacklist")),
# ):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.blacklist_customer(db, c, body.reason, current_user.id)

# @router.post("/customers/{customer_id}/remove-blacklist", response_model=schemas.CustomerOut)
# def remove_blacklist(
#     customer_id: int, db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:blacklist")),
# ):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.remove_blacklist(db, c, current_user.id)

# @router.post("/customers/{customer_id}/grant-vip", response_model=schemas.CustomerOut)
# def grant_vip(
#     customer_id: int, db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:vip_grant")),
# ):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.grant_vip(db, c, current_user.id)

# @router.post("/customers/{customer_id}/revoke-vip", response_model=schemas.CustomerOut)
# def revoke_vip(customer_id: int, db: Session = Depends(get_db), _=Depends(require_permission("customers:vip_grant"))):
#     c = controller.get_customer(db, customer_id)
#     if not c:
#         raise HTTPException(404, "Customer not found")
#     return controller.revoke_vip(db, c)

# # ── KYC ──────────────────────────────────────────────────────────────────────

# @router.post("/customers/{customer_id}/kyc", response_model=schemas.KYCOut, status_code=201)
# def submit_kyc(customer_id: int, body: schemas.KYCSubmit, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     return controller.submit_kyc(db, customer_id, body.model_dump())

# @router.get("/customers/{customer_id}/kyc", response_model=list[schemas.KYCOut])
# def get_kyc(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     return db.query(CustomerKYC).filter_by(customer_id=customer_id).all()

# @router.post("/kyc/{kyc_id}/review", response_model=schemas.KYCOut)
# def review_kyc(
#     kyc_id: int, body: schemas.KYCReview,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_permission("customers:kyc_verify")),
# ):
#     kyc = db.query(CustomerKYC).filter_by(id=kyc_id).first()
#     if not kyc:
#         raise HTTPException(404, "KYC record not found")
#     return controller.review_kyc(db, kyc, body.decision, current_user.id, body.note)

# # ── Contacts ──────────────────────────────────────────────────────────────────

# @router.post("/customers/{customer_id}/contacts", response_model=schemas.ContactOut, status_code=201)
# def add_contact(customer_id: int, body: schemas.ContactCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     return controller.add_contact(db, customer_id, body.model_dump())

# @router.get("/customers/{customer_id}/contacts", response_model=list[schemas.ContactOut])
# def list_contacts(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     from app.modules.customers.models import CustomerContact
#     return db.query(CustomerContact).filter_by(customer_id=customer_id).all()

# # ── Notes ─────────────────────────────────────────────────────────────────────

# @router.post("/customers/{customer_id}/notes", response_model=schemas.NoteOut, status_code=201)
# def add_note(customer_id: int, body: schemas.NoteCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
#     return controller.add_note(db, customer_id, body.content, current_user.id)

# @router.get("/customers/{customer_id}/notes", response_model=list[schemas.NoteOut])
# def list_notes(customer_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
#     from app.modules.customers.models import CustomerNote
#     return db.query(CustomerNote).filter_by(customer_id=customer_id).all()

# # ── Suppliers ─────────────────────────────────────────────────────────────────

# @router.post("/suppliers", response_model=schemas.SupplierOut, status_code=201)
# def create_supplier(
#     body: schemas.SupplierCreate, db: Session = Depends(get_db),
#     current_user=Depends(require_permission("procurement:create")),
# ):
#     data = body.model_dump()
#     if not current_user.is_superadmin:
#         data["company_id"] = current_user.company_id
#     return controller.create_supplier(db, data, current_user.id)

# @router.get("/suppliers", response_model=list[schemas.SupplierOut])
# def list_suppliers(db: Session = Depends(get_db), current_user=Depends(require_permission("procurement:read"))):
#     return controller.list_suppliers(db, current_user.company_id)

# @router.get("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
# def get_supplier(supplier_id: int, db: Session = Depends(get_db), _=Depends(require_permission("procurement:read"))):
#     s = controller.get_supplier(db, supplier_id)
#     if not s:
#         raise HTTPException(404, "Supplier not found")
#     return s


"""TEHTEK — Customers Router. ACC-007: auth at router level."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.companies.models import Company
from app.modules.customers import controller, schemas
from app.modules.companies.models import Company
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
    company_id = current_user.company_id
    if not company_id:
        company = db.query(Company).filter_by(code="TEHTEK").first()
        if company:
            company_id = company.id
    data["company_id"] = company_id
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
    # Live outstanding: unpaid invoices + manual receivables (those without an
    # invoice_number, to avoid double counting invoice-mirrored receivables).
    from app.modules.finance.models import Invoice
    from app.modules.finance.extended_models import Receivable
    out_cur: dict = {}
    for i in db.query(Invoice).filter(
        Invoice.customer_id == customer_id,
        Invoice.status.notin_(["cancelled"]),
    ).all():
        amt0 = float(i.balance_due or 0)
        if amt0 <= 0:
            continue
        cur = getattr(i, "currency", None) or "XAF"
        out_cur[cur] = out_cur.get(cur, 0.0) + amt0
    for r in db.query(Receivable).filter(
        Receivable.client_id == customer_id,
        Receivable.invoice_number.is_(None),
        Receivable.status.notin_(["collected", "written_off"]),
    ).all():
        cur = r.currency or "XAF"
        out_cur[cur] = out_cur.get(cur, 0.0) + float(r.balance_due or 0)
    out_cur = {k: round(v, 2) for k, v in out_cur.items() if v > 0}
    # Split: livré-en-attente vs confirmé-non-livré (via the invoice's source doc)
    from app.modules.orders.models import Order
    awaiting: dict = {}
    confirmed: dict = {}
    for i in db.query(Invoice).filter(
        Invoice.customer_id == customer_id,
        Invoice.status.notin_(["cancelled"]),
    ).all():
        cur = getattr(i, "currency", None) or "XAF"
        amt = float(i.balance_due or 0)
        if amt <= 0:
            continue
        delivered = True
        if i.ref_model == "shipment" and i.ref_id:
            sh0 = db.query(__import__("app.modules.cargo.models", fromlist=["Shipment"]).Shipment).filter_by(id=i.ref_id).first()
            delivered = bool(sh0 and sh0.status == "delivered")
        elif i.ref_model == "order" and i.ref_id:
            o = db.query(Order).filter_by(id=i.ref_id).first()
            delivered = bool(o.delivered) if o else True
        elif i.ref_model == "service_project" and i.ref_id:
            from app.modules.service_projects.models import ServiceProject as SP2
            pr2 = db.query(SP2).filter_by(id=i.ref_id).first()
            delivered = bool(pr2.delivered) if pr2 else True
        bucket = awaiting if delivered else confirmed
        bucket[cur] = bucket.get(cur, 0.0) + amt
    for r in db.query(Receivable).filter(
        Receivable.client_id == customer_id,
        Receivable.invoice_number.is_(None),
        Receivable.status.notin_(["collected", "written_off"]),
    ).all():
        amt = float(r.balance_due or 0)
        if amt > 0:
            cur = r.currency or "XAF"
            awaiting[cur] = awaiting.get(cur, 0.0) + amt
    from app.modules.service_projects.models import ServiceProject as SP3
    for pr3 in db.query(SP3).filter(
        SP3.customer_id == customer_id,
        SP3.invoice_id.is_(None),
        SP3.status.notin_(["cancelled", "delivered"]),
    ).all():
        cur = pr3.currency or "XAF"
        confirmed[cur] = confirmed.get(cur, 0.0) + float(pr3.total or 0)
    c.awaiting_by_currency = {k: round(v, 2) for k, v in awaiting.items() if v > 0}
    c.confirmed_by_currency = {k: round(v, 2) for k, v in confirmed.items() if v > 0}

    # Ventilation par objet : d'où vient chaque paiement attendu
    sources: dict = {}
    def _add_src(kind, label, cur, amt):
        if amt <= 0:
            return
        g = sources.setdefault(kind, {"kind": kind, "count": 0, "by_currency": {}, "items": []})
        g["count"] += 1
        g["by_currency"][cur] = round(g["by_currency"].get(cur, 0.0) + amt, 2)
        if len(g["items"]) < 10:
            g["items"].append({"label": label, "amount": round(amt, 2), "currency": cur})
    from app.modules.cargo.models import Shipment
    for i in db.query(Invoice).filter(
        Invoice.customer_id == customer_id,
        Invoice.status.notin_(["cancelled"]),
    ).all():
        amt = float(i.balance_due or 0)
        cur = getattr(i, "currency", None) or "XAF"
        label = i.invoice_number
        kind = i.ref_model or "facture"
        if i.ref_model == "shipment" and i.ref_id:
            sh = db.query(Shipment).filter_by(id=i.ref_id).first()
            if sh and sh.tracking_number:
                label = sh.tracking_number
        elif i.ref_model == "order" and i.ref_id:
            o2 = db.query(Order).filter_by(id=i.ref_id).first()
            if o2:
                label = o2.order_number
        elif i.ref_model == "service_project" and i.ref_id:
            from app.modules.service_projects.models import ServiceProject as SP4
            p4 = db.query(SP4).filter_by(id=i.ref_id).first()
            if p4:
                label = p4.reference
        _add_src(kind, label, cur, amt)
    for r in db.query(Receivable).filter(
        Receivable.client_id == customer_id,
        Receivable.invoice_number.is_(None),
        Receivable.status.notin_(["collected", "written_off"]),
    ).all():
        _add_src("receivable", r.receivable_number or r.ref_label, r.currency or "XAF",
                 float(r.balance_due or 0))
    from app.modules.service_projects.models import ServiceProject as SP5
    for p5 in db.query(SP5).filter(
        SP5.customer_id == customer_id,
        SP5.invoice_id.is_(None),
        SP5.status.notin_(["cancelled", "delivered"]),
    ).all():
        _add_src("service_project", p5.reference, p5.currency or "XAF", float(p5.total or 0))
    c.payment_sources = list(sources.values())

    c.outstanding_by_currency = out_cur
    c.outstanding_balance = out_cur.get("XAF", 0.0)
    # Committed but not yet invoiced: active projects, shown as a separate line.
    from app.modules.service_projects.models import ServiceProject
    pend_cur: dict = {}
    for pr in db.query(ServiceProject).filter(
        ServiceProject.customer_id == customer_id,
        ServiceProject.invoice_id.is_(None),
        ServiceProject.status.notin_(["cancelled", "delivered"]),
    ).all():
        cur = pr.currency or "XAF"
        pend_cur[cur] = pend_cur.get(cur, 0.0) + float(pr.total or 0)
    pend_cur = {k: round(v, 2) for k, v in pend_cur.items() if v > 0}
    c.pending_by_currency = pend_cur
    c.pending_projects_total = pend_cur.get("XAF", 0.0)
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

@router.patch("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(
    supplier_id: int, body: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("procurement:create")),
):
    s = controller.update_supplier(db, supplier_id, current_user.company_id, body.model_dump(exclude_unset=True))
    if not s:
        raise HTTPException(404, "Supplier not found")
    return s

@router.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("procurement:create")),
):
    if not controller.delete_supplier(db, supplier_id, current_user.company_id):
        raise HTTPException(404, "Supplier not found")
