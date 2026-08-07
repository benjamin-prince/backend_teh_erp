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
    type:          Optional[str] = None
    due_at:        Optional[datetime] = None
    status:        Optional[str] = None
    notes:         Optional[str] = None
    notify_wa:     Optional[bool] = None
    notify_wa_to:  Optional[str] = None


class SnoozeIn(BaseModel):
    days:  int = 0
    hours: int = 0


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
