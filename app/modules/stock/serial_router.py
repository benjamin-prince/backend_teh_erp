"""
TEHTEK — Batch & Serial Traceability API

Endpoints (all require auth via router-level dependency in main.py):
  POST   /batches                     — receive a batch (creates batch + serials)
  GET    /batches                     — list batches (paginated)
  GET    /batches/{id}                — batch detail + all serials
  GET    /serials                     — search/list serials
  GET    /serials/trace/{serial}      — full trace of one serial number
  PATCH  /serials/{id}               — update serial (sell, return, notes, status)
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, enforce_company_scope
from app.core.enums import SerialStatus, SequenceType
from app.modules.companies.controller import next_sequence
from app.modules.stock.models import Product, SerialNumber, SupplierBatch

router = APIRouter(prefix="/api/v1", tags=["traceability"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SerialIn(BaseModel):
    serial_number: Optional[str] = None  # None → auto-generate

class BatchCreate(BaseModel):
    product_id:    int
    quantity:      int
    supplier_name: Optional[str] = None
    unit_cost:     Optional[float] = None
    received_date: Optional[datetime] = None
    notes:         Optional[str] = None
    serials:       Optional[List[SerialIn]] = None  # provide list OR leave empty for auto

class SerialUpdate(BaseModel):
    status:        Optional[str] = None
    customer_id:   Optional[int] = None
    customer_name: Optional[str] = None
    sold_at:       Optional[datetime] = None
    returned_at:   Optional[datetime] = None
    return_reason: Optional[str] = None
    notes:         Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serial_out(s: SerialNumber) -> dict:
    return {
        "id":            s.id,
        "serial_number": s.serial_number,
        "product_id":    s.product_id,
        "product_name":  s.product.name if s.product else None,
        "product_sku":   s.product.sku  if s.product else None,
        "batch_id":      s.batch_id,
        "batch_number":  s.batch.batch_number if s.batch else None,
        "is_generated":  s.is_generated,
        "status":        s.status,
        "customer_id":   s.customer_id,
        "customer_name": s.customer_name,
        "sold_at":       s.sold_at.isoformat() if s.sold_at else None,
        "returned_at":   s.returned_at.isoformat() if s.returned_at else None,
        "return_reason": s.return_reason,
        "notes":         s.notes,
        "created_at":    s.created_at.isoformat(),
        "updated_at":    s.updated_at.isoformat() if s.updated_at else None,
    }


def _batch_out(b: SupplierBatch, include_serials: bool = False) -> dict:
    out = {
        "id":            b.id,
        "batch_number":  b.batch_number,
        "product_id":    b.product_id,
        "product_name":  b.product.name if b.product else None,
        "product_sku":   b.product.sku  if b.product else None,
        "supplier_name": b.supplier_name,
        "quantity":      b.quantity,
        "unit_cost":     float(b.unit_cost) if b.unit_cost else None,
        "received_date": b.received_date.isoformat() if b.received_date else None,
        "notes":         b.notes,
        "created_at":    b.created_at.isoformat(),
        "serial_count":  len(b.serials) if b.serials else 0,
    }
    if include_serials:
        out["serials"] = [_serial_out(s) for s in b.serials if s.deleted_at is None]
    return out


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/batches")
def receive_batch(
    body: BatchCreate,
    db:   Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    Receive a batch from a supplier.
    - If `serials` list provided: use those serial numbers (auto-generate for empty strings)
    - If `serials` not provided: auto-generate all `quantity` serial numbers
    """
    company_id = user.company_id

    q = db.query(Product).filter(Product.id == body.product_id, Product.deleted_at.is_(None))
    q = enforce_company_scope(user, q, Product)
    product = q.first()
    if not product:
        raise HTTPException(404, "Product not found")

    if body.quantity < 1:
        raise HTTPException(422, "quantity must be ≥ 1")

    batch_no = next_sequence(db, SequenceType.batch_number)
    batch = SupplierBatch(
        batch_number  = batch_no,
        product_id    = body.product_id,
        company_id    = company_id,
        supplier_name = body.supplier_name,
        quantity      = body.quantity,
        unit_cost     = body.unit_cost,
        received_date = body.received_date or datetime.utcnow(),
        notes         = body.notes,
        created_by    = user.id,
    )
    db.add(batch)
    db.flush()  # get batch.id

    # Build serial list
    provided = list(body.serials or [])
    while len(provided) < body.quantity:
        provided.append(SerialIn())

    for entry in provided[:body.quantity]:
        sn_str = (entry.serial_number or "").strip()
        is_gen = False
        if not sn_str:
            sn_str = next_sequence(db, SequenceType.serial_number)
            is_gen = True

        if db.query(SerialNumber).filter_by(serial_number=sn_str).first():
            raise HTTPException(409, f"Serial '{sn_str}' already exists")

        sn = SerialNumber(
            serial_number = sn_str,
            product_id    = body.product_id,
            batch_id      = batch.id,
            company_id    = company_id,
            is_generated  = is_gen,
            status        = SerialStatus.in_stock,
            created_by    = user.id,
        )
        db.add(sn)

    db.commit()
    db.refresh(batch)
    return _batch_out(batch, include_serials=True)


@router.get("/batches")
def list_batches(
    product_id: Optional[int] = Query(None),
    page:       int = Query(1, ge=1),
    per_page:   int = Query(20, ge=1, le=100),
    db:         Session = Depends(get_db),
    user = Depends(get_current_user),
):
    q = db.query(SupplierBatch).filter(SupplierBatch.deleted_at.is_(None))
    q = enforce_company_scope(user, q, SupplierBatch)
    if product_id:
        q = q.filter(SupplierBatch.product_id == product_id)
    total = q.count()
    batches = q.order_by(SupplierBatch.id.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": [_batch_out(b) for b in batches],
    }


@router.get("/batches/{batch_id}")
def get_batch(
    batch_id: int,
    db:       Session = Depends(get_db),
    user = Depends(get_current_user),
):
    q = db.query(SupplierBatch).filter(
        SupplierBatch.id == batch_id,
        SupplierBatch.deleted_at.is_(None),
    )
    q = enforce_company_scope(user, q, SupplierBatch)
    b = q.first()
    if not b:
        raise HTTPException(404, "Batch not found")
    return _batch_out(b, include_serials=True)


@router.get("/serials")
def list_serials(
    product_id: Optional[int]  = Query(None),
    batch_id:   Optional[int]  = Query(None),
    status:     Optional[str]  = Query(None),
    search:     Optional[str]  = Query(None),
    page:       int = Query(1, ge=1),
    per_page:   int = Query(30, ge=1, le=100),
    db:         Session = Depends(get_db),
    user = Depends(get_current_user),
):
    q = db.query(SerialNumber).filter(SerialNumber.deleted_at.is_(None))
    q = enforce_company_scope(user, q, SerialNumber)
    if product_id: q = q.filter(SerialNumber.product_id == product_id)
    if batch_id:   q = q.filter(SerialNumber.batch_id == batch_id)
    if status:     q = q.filter(SerialNumber.status == status)
    if search:
        q = q.filter(SerialNumber.serial_number.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(SerialNumber.id.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": [_serial_out(s) for s in items],
    }


@router.get("/serials/trace/{serial_number}")
def trace_serial(
    serial_number: str,
    db:            Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """Full traceability: supplier batch → current status → customer/return."""
    q = db.query(SerialNumber).filter(
        SerialNumber.serial_number == serial_number,
        SerialNumber.deleted_at.is_(None),
    )
    q = enforce_company_scope(user, q, SerialNumber)
    s = q.first()
    if not s:
        raise HTTPException(404, f"Serial '{serial_number}' not found")

    out = _serial_out(s)
    if s.batch:
        out["batch"] = {
            "batch_number":  s.batch.batch_number,
            "supplier_name": s.batch.supplier_name,
            "received_date": s.batch.received_date.isoformat() if s.batch.received_date else None,
            "unit_cost":     float(s.batch.unit_cost) if s.batch.unit_cost else None,
        }
    return out


@router.patch("/serials/{serial_id}")
def update_serial(
    serial_id: int,
    body:      SerialUpdate,
    db:        Session = Depends(get_db),
    user = Depends(get_current_user),
):
    q = db.query(SerialNumber).filter(
        SerialNumber.id == serial_id,
        SerialNumber.deleted_at.is_(None),
    )
    q = enforce_company_scope(user, q, SerialNumber)
    s = q.first()
    if not s:
        raise HTTPException(404, "Serial not found")

    if body.status is not None:
        try:
            s.status = SerialStatus(body.status)
        except ValueError:
            raise HTTPException(422, f"Invalid status '{body.status}'")

    if body.customer_id   is not None: s.customer_id   = body.customer_id
    if body.customer_name is not None: s.customer_name = body.customer_name
    if body.sold_at       is not None: s.sold_at       = body.sold_at
    if body.returned_at   is not None: s.returned_at   = body.returned_at
    if body.return_reason is not None: s.return_reason = body.return_reason
    if body.notes         is not None: s.notes         = body.notes

    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _serial_out(s)
