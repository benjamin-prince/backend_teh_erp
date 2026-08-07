"""
Reminders / Scheduler API — payment-to-receive, pickup, delivery and custom
reminders. Single-company tool (auth at router level, scoped by company_id).

Endpoints:
  GET    /api/v1/reminders            — list (status/type filters)
  GET    /api/v1/reminders/stats      — counts for the header bell
  POST   /api/v1/reminders            — create
  PATCH  /api/v1/reminders/{id}       — edit
  POST   /api/v1/reminders/{id}/complete
  POST   /api/v1/reminders/{id}/snooze   {days|hours}
  DELETE /api/v1/reminders/{id}
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.reminders.models import Reminder

router = APIRouter(
    prefix="/api/v1/reminders",
    tags=["Reminders"],
    dependencies=[Depends(get_current_user)],
)

VALID_TYPES = {"payment", "pickup", "delivery", "custom"}


# ── Schemas ─────────────────────────────────────────────────────────────────
class ReminderIn(BaseModel):
    title:         str                      # the description (required)
    contact_name:  str                      # required
    contact_phone: str                      # required
    type:          str = "custom"
    due_at:        datetime
    address:       Optional[str] = None      # optional (pickup)
    fee_amount:    Optional[float] = None     # pickup fee (recorded on confirm)
    fee_currency:  Optional[str] = None
    ref_model:     Optional[str] = None
    ref_id:        Optional[int] = None
    customer_id:   Optional[int] = None
    notes:         Optional[str] = None
    notify_wa:     bool = True
    notify_wa_to:  Optional[str] = None


class ReminderPatch(BaseModel):
    title:         Optional[str] = None
    contact_name:  Optional[str] = None
    contact_phone: Optional[str] = None
    address:       Optional[str] = None
    fee_amount:    Optional[float] = None
    fee_currency:  Optional[str] = None
    type:          Optional[str] = None
    due_at:        Optional[datetime] = None
    status:        Optional[str] = None
    notes:         Optional[str] = None
    notify_wa:     Optional[bool] = None
    notify_wa_to:  Optional[str] = None


class SnoozeIn(BaseModel):
    days:  int = 0
    hours: int = 0


class ValidatePayIn(BaseModel):
    amount:         Optional[float] = None   # defaults to the full outstanding balance
    payment_method: str = "cash"
    currency:       Optional[str] = None


def _out(r: Reminder) -> dict:
    return {c.name: getattr(r, c.name) for c in r.__table__.columns}


# ── Routes ──────────────────────────────────────────────────────────────────
@router.get("")
def list_reminders(
    status: str = "pending",       # pending | done | cancelled | all
    type:   Optional[str] = None,
    limit:  int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Reminder).filter(Reminder.company_id == current_user.company_id)
    if status and status != "all":
        q = q.filter(Reminder.status == status)
    if type:
        q = q.filter(Reminder.type == type)
    order = Reminder.completed_at.desc() if status == "done" else Reminder.due_at.asc()
    return [_out(r) for r in q.order_by(order).limit(limit).all()]


@router.get("/stats")
def reminder_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    now = datetime.utcnow()
    end_today = now.replace(hour=23, minute=59, second=59, microsecond=0)
    base = db.query(Reminder).filter(
        Reminder.company_id == current_user.company_id,
        Reminder.status == "pending",
    )
    overdue  = base.filter(Reminder.due_at < now).count()
    today    = base.filter(Reminder.due_at >= now, Reminder.due_at <= end_today).count()
    upcoming = base.filter(Reminder.due_at > end_today).count()
    # The bell badge = things that need attention now.
    return {"overdue": overdue, "today": today, "upcoming": upcoming, "due": overdue + today}


@router.post("", status_code=201)
def create_reminder(
    body: ReminderIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if body.type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of {sorted(VALID_TYPES)}")
    if not body.title.strip():
        raise HTTPException(400, "description is required")
    if not body.contact_name.strip():
        raise HTTPException(400, "contact name is required")
    if not body.contact_phone.strip():
        raise HTTPException(400, "contact number is required")
    r = Reminder(
        company_id=current_user.company_id,
        title=body.title.strip(),
        contact_name=body.contact_name.strip(),
        contact_phone=body.contact_phone.strip(),
        address=(body.address or "").strip() or None,
        fee_amount=body.fee_amount if (body.fee_amount and body.fee_amount > 0) else None,
        fee_currency=(body.fee_currency or "XAF") if body.fee_amount else None,
        type=body.type,
        due_at=body.due_at,
        ref_model=body.ref_model,
        ref_id=body.ref_id,
        customer_id=body.customer_id,
        notes=body.notes,
        notify_wa=body.notify_wa,
        notify_wa_to=body.notify_wa_to,
        created_by=current_user.id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.patch("/{reminder_id}")
def update_reminder(
    reminder_id: int,
    body: ReminderPatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    data = body.model_dump(exclude_unset=True)
    if "type" in data and data["type"] not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of {sorted(VALID_TYPES)}")
    for k, v in data.items():
        setattr(r, k, v)
    # Re-arming a reminder (new due date / back to pending) clears the push latch.
    if "due_at" in data or data.get("status") == "pending":
        r.notified_at = None
    if data.get("status") == "done":
        r.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return _out(r)


@router.post("/{reminder_id}/complete")
def complete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    r.status = "done"
    r.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return _out(r)


@router.post("/{reminder_id}/snooze")
def snooze_reminder(
    reminder_id: int,
    body: SnoozeIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    delta = timedelta(days=body.days, hours=body.hours)
    if delta.total_seconds() <= 0:
        raise HTTPException(400, "snooze must be a positive duration")
    # Snooze from now (not the old due date) so an overdue item moves into the future.
    base = max(r.due_at, datetime.utcnow())
    r.due_at = base + delta
    r.status = "pending"
    r.notified_at = None
    db.commit()
    db.refresh(r)
    return _out(r)


# ── Business actions ────────────────────────────────────────────────────────
@router.post("/{reminder_id}/confirm-pickup")
def confirm_pickup(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Turn a pickup reminder into a draft shipment: the contact becomes the
    sender (and the customer, found-or-created by phone), the description becomes
    the content. Marks the reminder done and links it to the new shipment."""
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    # Already confirmed → return the existing shipment instead of duplicating.
    if r.status == "done" and r.ref_model == "shipment" and r.ref_id:
        return {"shipment_id": r.ref_id, "reminder": _out(r), "already": True}

    from app.modules.cargo.models import Shipment
    from app.modules.customers.models import Customer
    from app.modules.customers.controller import create_customer

    # Resolve the customer: reminder's own, else find-or-create by phone.
    cust_id = r.customer_id
    if not cust_id:
        phone = (r.contact_phone or "").strip()
        cust = None
        if phone:
            cust = (
                db.query(Customer)
                .filter(Customer.company_id == current_user.company_id,
                        Customer.phone == phone, Customer.deleted_at.is_(None))
                .first()
            )
        if not cust:
            name = (r.contact_name or "Client").strip()
            first, _, last = name.partition(" ")
            cust = create_customer(db, {
                "company_id": current_user.company_id,
                "first_name": first or "Client",
                "last_name": last or "-",
                "phone": phone or None,
                "customer_type": "shipping",   # required (no model default); TehCargo sender
            }, current_user.id)
        cust_id = cust.id

    s = Shipment(
        company_id=current_user.company_id,
        branch_id=current_user.branch_id,
        customer_id=cust_id,
        shipment_type="sea_freight",   # sensible default; editable on the shipment page
        route_legacy="",               # NOT NULL (mirrors create_shipment's default)
        status="draft",
        sender_name=r.contact_name,
        sender_phone=r.contact_phone,
        sender_address=r.address,
        content_description=r.title,
        pickup_type="pickup_request",
        created_by=current_user.id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    # Record the pickup fee as an income transaction (Finance → Income).
    income = None
    fee = float(r.fee_amount or 0)
    if fee > 0:
        from app.modules.finance.extended_models import IncomeRecord
        from app.modules.finance.extended_router import _next_number
        cur = r.fee_currency or "XAF"
        num = _next_number(db, IncomeRecord, IncomeRecord.company_id, "INC", current_user.company_id)
        db.add(IncomeRecord(
            company_id=current_user.company_id, branch_id=current_user.branch_id,
            income_number=num, date=datetime.utcnow(),
            description=f"Frais d'enlèvement — {r.title}", category="pickup_fee",
            ref_model="shipment", ref_id=s.id, ref_label=s.tracking_number or r.title,
            customer_id=cust_id, tracking_number=s.tracking_number,
            amount=fee, currency=cur, exchange_rate=1, amount_base=fee,
            payment_method="cash", status="received", created_by=current_user.id,
        ))
        income = {"income_number": num, "amount": fee, "currency": cur}

    r.status = "done"
    r.completed_at = datetime.utcnow()
    r.ref_model = "shipment"
    r.ref_id = s.id
    db.commit()
    db.refresh(r)
    return {"shipment_id": s.id, "customer_id": cust_id, "income": income, "reminder": _out(r)}


@router.post("/{reminder_id}/validate-payment")
def validate_payment(
    reminder_id: int,
    body: ValidatePayIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Record a payment against the invoice linked to this reminder (defaults to
    the full outstanding balance) and mark the reminder done."""
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")

    from app.modules.finance.models import Invoice, Payment
    from app.core.enums import PaymentStatus, SequenceType
    from app.modules.companies.controller import next_sequence

    inv = None
    if r.ref_model == "invoice" and r.ref_id:
        inv = db.query(Invoice).filter_by(id=r.ref_id, deleted_at=None).first()
    elif r.ref_model == "shipment" and r.ref_id:
        inv = (
            db.query(Invoice)
            .filter_by(ref_model="shipment", ref_id=r.ref_id, deleted_at=None)
            .filter(Invoice.status != "cancelled")
            .order_by(Invoice.id.desc())
            .first()
        )
    if not inv:
        raise HTTPException(400, "No invoice is linked to this reminder — generate one first.")

    now = datetime.utcnow()
    balance = float(inv.total or 0) - float(inv.paid_amount or 0)
    amount = body.amount if (body.amount and body.amount > 0) else balance
    if amount <= 0:
        r.status, r.completed_at = "done", now
        db.commit()
        db.refresh(r)
        return {"invoice_id": inv.id, "amount": 0, "reminder": _out(r)}

    receipt = next_sequence(db, SequenceType.receipt_number)
    db.add(Payment(
        company_id=current_user.company_id, invoice_id=inv.id, customer_id=inv.customer_id,
        receipt_number=receipt, payment_method=body.payment_method, amount=amount,
        currency=body.currency or inv.currency, status=PaymentStatus.confirmed,
        created_by=current_user.id, confirmed_by=current_user.id, confirmed_at=now,
    ))
    inv.paid_amount = float(inv.paid_amount or 0) + amount
    inv.balance_due = float(inv.total) - float(inv.paid_amount)
    if inv.balance_due <= 0:
        inv.status, inv.paid_at = "paid", now
    elif float(inv.paid_amount) > 0:
        inv.status = "partial"
    inv.updated_at = now
    r.status, r.completed_at = "done", now
    db.commit()
    db.refresh(r)
    return {"invoice_id": inv.id, "receipt_number": receipt, "amount": amount,
            "balance_due": float(inv.balance_due), "reminder": _out(r)}


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = db.query(Reminder).filter_by(id=reminder_id, company_id=current_user.company_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    db.delete(r)
    db.commit()
