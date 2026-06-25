"""
app/modules/service_projects/controller.py
Business logic for Service Projects (IT & Security)

Changes vs original:
- create_service_type: auto-generate unique code; handle unit field
- create_project: write title+description to milestone; set project_number;
                  parse "YYYY-MM-DD" date strings; sync apply_tva/include_tax
- update_project: handle apply_tva; stamp workflow timestamps; parse date strings
- skip_br: stamp br_received_at; record approved_by
- generate_invoice: stamp invoiced_at; use title in line items
- create_milestone / update_milestone: write title+line_total
"""
import re
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.service_projects.models import (
    ServiceProject, ServiceMilestone, ServiceType,
    ServiceProjectStatus,
)
from app.modules.service_projects.schemas import (
    ServiceProjectCreate, ServiceProjectUpdate,
    MilestoneCreate, MilestoneUpdate,
    ServiceTypeCreate, ServiceTypeUpdate,
    SkipBrPayload,
)

TAX_RATE = Decimal("0.1925")

# Status → timestamp column name
_TS = {
    "proposal_sent": "proposal_sent_at",
    "signed":        "signed_at",
    "bl_sent":       "bl_sent_at",
    "br_received":   "br_received_at",
    "invoiced":      "invoiced_at",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _next_reference(db: Session) -> str:
    prefix = "SP-" + datetime.utcnow().strftime("%Y%m")
    count  = db.query(ServiceProject).filter(
        ServiceProject.reference.like(f"{prefix}%")
    ).count()
    return f"{prefix}-{count + 1:04d}"


def _slugify(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:40]


def _unique_code(db: Session, raw: str) -> str:
    base = raw or "SVC"
    attempt, n = base, 1
    while db.query(ServiceType).filter_by(code=attempt).first():
        attempt = f"{base}_{n}"
        n += 1
    return attempt


def _recalculate(project: ServiceProject) -> None:
    """total = subtotal + TVA − retenue − discount. One tax type at a time.

    tax_type: none | tva | retenue. tax_rate is a percent (e.g. 19.25).
    price_inclusive (TVA only): entered prices are TTC → extract TVA from the base.
    Legacy apply_tva/include_tax still imply TVA at 19.25% when tax_type is unset.
    """
    cents = Decimal("0.01")
    raw = sum((m.line_total or m.total or Decimal("0")) for m in project.milestones)
    disc = project.discount_amount or Decimal("0")

    tax_type = (project.tax_type or "none").lower()
    if tax_type == "none" and (project.apply_tva or project.include_tax):
        tax_type, rate = "tva", TAX_RATE      # legacy fallback
    else:
        rate = (Decimal(str(project.tax_rate or 0)) / Decimal("100"))

    if tax_type == "tva":
        if project.price_inclusive and rate:
            project.subtotal = (raw / (1 + rate)).quantize(cents)
            project.tax_amount = (raw - project.subtotal).quantize(cents)
        else:
            project.subtotal = Decimal(raw).quantize(cents)
            project.tax_amount = (raw * rate).quantize(cents)
        project.retenue_amount = Decimal("0")
        project.total = (project.subtotal + project.tax_amount - disc).quantize(cents)
    elif tax_type == "retenue":
        project.subtotal = Decimal(raw).quantize(cents)
        project.tax_amount = Decimal("0")
        project.retenue_amount = (raw * rate).quantize(cents)
        project.total = (project.subtotal - project.retenue_amount - disc).quantize(cents)
    else:
        project.subtotal = Decimal(raw).quantize(cents)
        project.tax_amount = Decimal("0")
        project.retenue_amount = Decimal("0")
        project.total = (project.subtotal - disc).quantize(cents)


def _milestone_line_total(m: ServiceMilestone) -> Decimal:
    return (m.quantity * m.unit_price).quantize(Decimal("0.01"))


def _parse_date(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v), "%Y-%m-%d")
    except ValueError:
        return None


# ── ServiceType CRUD ──────────────────────────────────────────────────────────

def list_service_types(
    db: Session,
    active_only: bool = False,
    category: Optional[str] = None,
) -> List[ServiceType]:
    q = db.query(ServiceType)
    if active_only:
        q = q.filter(ServiceType.is_active == True)  # noqa: E712
    if category:
        q = q.filter(ServiceType.category == category)
    return q.order_by(ServiceType.name).all()


def create_service_type(db: Session, payload: ServiceTypeCreate) -> ServiceType:
    raw_code = payload.code or _slugify(payload.name)
    code     = _unique_code(db, raw_code)
    obj = ServiceType(
        code        = code,
        name        = payload.name,
        unit        = payload.unit or "forfait",
        category    = payload.category,
        description = payload.description,
        unit_price  = payload.unit_price,
        is_active   = payload.is_active,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_service_type(db: Session, type_id: int, payload: ServiceTypeUpdate) -> ServiceType:
    obj = db.query(ServiceType).filter_by(id=type_id).first()
    if not obj:
        raise HTTPException(404, "ServiceType not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_service_type(db: Session, type_id: int) -> None:
    obj = db.query(ServiceType).filter_by(id=type_id).first()
    if not obj:
        raise HTTPException(404, "ServiceType not found")
    obj.is_active = False   # soft-delete
    db.commit()


# ── ServiceProject CRUD ───────────────────────────────────────────────────────

def list_projects(
    db:          Session,
    customer_id: Optional[int]                  = None,
    status:      Optional[ServiceProjectStatus] = None,
    category:    Optional[str]                  = None,
    exclude_category: Optional[str]             = None,
    skip:        int = 0,
    limit:       int = 100,
) -> List[ServiceProject]:
    q = db.query(ServiceProject)
    if customer_id:
        q = q.filter(ServiceProject.customer_id == customer_id)
    if status:
        q = q.filter(ServiceProject.status == status)
    if category:
        q = q.filter(ServiceProject.category == category)
    if exclude_category:
        q = q.filter(ServiceProject.category != exclude_category)
    return q.order_by(ServiceProject.id.desc()).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int) -> ServiceProject:
    obj = db.query(ServiceProject).filter_by(id=project_id).first()
    if not obj:
        raise HTTPException(404, "ServiceProject not found")
    return obj


def create_project(db: Session, payload: ServiceProjectCreate) -> ServiceProject:
    ref = _next_reference(db)
    project = ServiceProject(
        reference       = ref,
        project_number  = ref,       # keep both in sync
        title           = payload.title,
        customer_id     = payload.customer_id,
        service_type_id = payload.service_type_id,
        category        = payload.category,
        currency        = payload.currency,
        site_address    = payload.site_address,
        technician      = payload.technician,
        notes           = payload.notes,
        apply_tva       = payload.apply_tva,
        include_tax     = payload.apply_tva,   # keep legacy column in sync
        tax_type        = payload.tax_type,
        tax_rate        = Decimal(str(payload.tax_rate or 0)),
        price_inclusive = payload.price_inclusive,
        discount_amount = Decimal("0"),
        start_date      = _parse_date(payload.start_date),
        end_date        = _parse_date(payload.end_date),
    )
    db.add(project)
    db.flush()

    for i, ms in enumerate(payload.milestones):
        label = ms.title or ms.description or ""
        lt    = (ms.quantity * ms.unit_price).quantize(Decimal("0.01"))
        milestone = ServiceMilestone(
            project_id      = project.id,
            service_type_id = ms.service_type_id,
            title           = label,
            description     = label,
            quantity        = ms.quantity,
            unit_price      = ms.unit_price,
            line_total      = lt,
            total           = lt,
            serials         = ms.serials,
            sort_order      = ms.sort_order if ms.sort_order else i,
        )
        db.add(milestone)

    db.flush()
    db.refresh(project)
    _recalculate(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, project_id: int, payload: ServiceProjectUpdate,
) -> ServiceProject:
    project = get_project(db, project_id)
    if project.status == ServiceProjectStatus.cancelled:
        raise HTTPException(400, "Cannot update a cancelled project")

    changes    = payload.model_dump(exclude_unset=True)
    new_status = changes.get("status")

    for k, v in changes.items():
        if k in ("start_date", "end_date"):
            v = _parse_date(v)
        setattr(project, k, v)

    if "delivered" in changes:
        project.delivered_at = datetime.utcnow() if changes["delivered"] else None

    # Keep legacy include_tax in sync with apply_tva
    if "apply_tva" in changes:
        project.include_tax = changes["apply_tva"]
    # Recompute totals whenever the tax config or discount changes
    if changes.keys() & {"apply_tva", "tax_type", "tax_rate", "price_inclusive", "discount_amount"}:
        _recalculate(project)
        # Sync a still-draft, unpaid linked invoice so its document reflects the tax
        if project.invoice_id:
            from app.modules.finance.models import Invoice
            inv = db.query(Invoice).filter_by(id=project.invoice_id).first()
            if inv and inv.status == "draft" and (inv.paid_amount or Decimal("0")) == 0:
                inv.subtotal        = project.subtotal
                inv.tax_amount      = project.tax_amount
                inv.retenue_amount  = project.retenue_amount
                inv.discount_amount = project.discount_amount
                inv.total           = project.total
                inv.balance_due     = project.total
                inv.tax_type        = project.tax_type or "none"
                inv.tax_rate        = project.tax_rate or Decimal("0")

    # Stamp workflow timestamp when status advances
    if new_status and new_status in _TS:
        ts_col = _TS[new_status]
        if not getattr(project, ts_col):
            setattr(project, ts_col, datetime.utcnow())

    db.commit()
    db.refresh(project)
    return project


def skip_br(
    db: Session, project_id: int, payload: SkipBrPayload,
) -> ServiceProject:
    project = get_project(db, project_id)
    allowed = {ServiceProjectStatus.bl_sent, ServiceProjectStatus.completed}
    if project.status not in allowed:
        raise HTTPException(400, f"skip-br only allowed in: {[s.value for s in allowed]}")
    project.skip_br        = True
    project.skip_br_reason = payload.reason
    project.status         = ServiceProjectStatus.br_received
    project.br_received_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


# ── Invoice ───────────────────────────────────────────────────────────────────

def generate_invoice(db: Session, project_id: int,
                     percentage: float = None, amount: float = None,
                     company_id: int = 1, created_by: int = None):
    from app.modules.finance.models import Invoice
    from app.modules.companies.controller import next_sequence
    from app.core.enums import SequenceType

    project = get_project(db, project_id)

    # If existing invoice has no payment yet, return it (avoid duplicate open invoices)
    if project.invoice_id:
        inv = db.query(Invoice).filter_by(id=project.invoice_id).first()
        if inv and inv.status != "cancelled" and (inv.paid_amount or 0) == 0:
            return inv

    import json

    # Cumulative paid across all invoices for this project (sum paid_amount, not just "paid" status)
    all_invs = db.query(Invoice).filter_by(ref_model="service_project", ref_id=project.id).all()
    total_previously_paid = sum(Decimal(str(i.paid_amount or 0)) for i in all_invs)

    project_total = project.total or Decimal("0")
    remaining = max(project_total - total_previously_paid, Decimal("0"))

    if amount is not None:
        inv_total = min(Decimal(str(amount)), remaining if remaining > 0 else project_total)
        inv_total = inv_total.quantize(Decimal("0.01"))
        factor = (inv_total / project_total) if project_total > 0 else Decimal("1")
        pct_display = round(float(factor) * 100)
    elif percentage is not None:
        factor = Decimal(str(min(max(percentage, 1), 100) / 100))
        inv_total = (project_total * factor).quantize(Decimal("0.01"))
        pct_display = int(percentage)
    else:
        # Default: full remaining balance
        inv_total = remaining if remaining > 0 else project_total
        factor = (inv_total / project_total) if project_total > 0 else Decimal("1")
        pct_display = round(float(factor) * 100)

    items = [
        {
            "description": m.title or m.description or "",
            "quantity":    float(m.quantity),
            "unit_price":  float(m.unit_price),
            "serials":     getattr(m, "serials", None),
            "total":       float((m.line_total or Decimal("0")) * factor),
        }
        for m in project.milestones
    ]

    subtotal = (project.subtotal        * factor).quantize(Decimal("0.01"))
    discount = (project.discount_amount * factor).quantize(Decimal("0.01"))
    tax      = (project.tax_amount      * factor).quantize(Decimal("0.01"))
    retenue  = ((project.retenue_amount or Decimal("0")) * factor).quantize(Decimal("0.01"))

    notes_parts = []
    if pct_display < 100:
        notes_parts.append(f"Facture partielle : {pct_display}% du montant total du projet.")
    if total_previously_paid > 0:
        cur = getattr(project, "currency", "XAF") or "XAF"
        notes_parts.append(f"Déjà facturé et payé : {int(total_previously_paid):,} {cur}.".replace(",", " "))
    if project.notes:
        notes_parts.append(project.notes)
    notes = "\n".join(notes_parts) or None

    inv = Invoice(
        company_id      = company_id,
        invoice_number  = next_sequence(db, SequenceType.invoice_number),
        invoice_type    = "sale",
        customer_id     = project.customer_id,
        ref_model       = "service_project",
        ref_id          = project.id,
        subtotal        = subtotal,
        discount_amount = discount,
        tax_amount      = tax,
        retenue_amount  = retenue,
        tax_type        = project.tax_type or "none",
        tax_rate        = project.tax_rate or Decimal("0"),
        total           = inv_total,
        paid_amount     = Decimal("0"),
        balance_due     = inv_total,
        line_items_json = json.dumps(items),
        notes           = notes,
        created_by      = created_by,
    )
    db.add(inv)
    db.flush()

    project.invoice_id  = inv.id
    project.status      = ServiceProjectStatus.invoiced
    project.invoiced_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return inv


def get_invoice(db: Session, project_id: int):
    from app.modules.finance.models import Invoice
    project = get_project(db, project_id)
    if not project.invoice_id:
        raise HTTPException(404, "No invoice generated for this project yet")
    inv = db.query(Invoice).filter_by(id=project.invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice record missing")
    return inv


# ── Milestone CRUD ────────────────────────────────────────────────────────────

def list_milestones(db: Session, project_id: int) -> List[ServiceMilestone]:
    get_project(db, project_id)
    return (
        db.query(ServiceMilestone)
        .filter_by(project_id=project_id)
        .order_by(ServiceMilestone.sort_order, ServiceMilestone.id)
        .all()
    )


def create_milestone(db: Session, project_id: int, payload: MilestoneCreate) -> ServiceMilestone:
    project = get_project(db, project_id)
    label   = payload.title or payload.description or ""
    lt      = (payload.quantity * payload.unit_price).quantize(Decimal("0.01"))
    m = ServiceMilestone(
        project_id      = project_id,
        service_type_id = payload.service_type_id,
        title           = label,
        description     = label,
        quantity        = payload.quantity,
        unit_price      = payload.unit_price,
        line_total      = lt,
        total           = lt,
        sort_order      = payload.sort_order,
    )
    db.add(m)
    db.flush()
    db.refresh(project)
    _recalculate(project)
    db.commit()
    db.refresh(m)
    return m


def update_milestone(
    db: Session, project_id: int, milestone_id: int, payload: MilestoneUpdate,
) -> ServiceMilestone:
    project = get_project(db, project_id)
    m = db.query(ServiceMilestone).filter_by(id=milestone_id, project_id=project_id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")

    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(m, k, v)
    # Keep title and description in sync
    if "title" in changes:
        m.description = changes["title"]
    elif "description" in changes:
        m.title = changes["description"]

    lt       = _milestone_line_total(m)
    m.total  = lt
    m.line_total = lt
    db.flush()
    db.refresh(project)
    _recalculate(project)
    db.commit()
    db.refresh(m)
    return m


def delete_milestone(db: Session, project_id: int, milestone_id: int) -> None:
    project = get_project(db, project_id)
    m = db.query(ServiceMilestone).filter_by(id=milestone_id, project_id=project_id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")
    db.delete(m)
    db.flush()
    db.refresh(project)
    _recalculate(project)
    db.commit()
