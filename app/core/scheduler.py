"""
TEHTEK background scheduler — runs in a daemon thread, no extra dependencies.
Jobs fire every hour on startup and then on a fixed interval.

Jobs:
  1. mark_overdue_invoices   — invoice.due_date < today and status not paid/cancelled → overdue
  2. mark_expiring_locations — lease_end within 30 days → expiring_soon
  3. mark_expired_locations  — lease_end in the past   → inactive
"""
import logging
import threading
import time
from datetime import datetime, timedelta

from app.core.database import SessionLocal

logger = logging.getLogger("tehtek.scheduler")

_INTERVAL_SECONDS = 3600  # run once per hour


# ── Job implementations ────────────────────────────────────────────────────────

def _mark_overdue_invoices(db) -> int:
    from app.modules.finance.models import Invoice

    now = datetime.utcnow()
    updated = (
        db.query(Invoice)
        .filter(
            Invoice.deleted_at.is_(None),
            Invoice.due_date < now,
            Invoice.status.notin_(["paid", "cancelled", "written_off", "overdue"]),
        )
        .update({"status": "overdue"}, synchronize_session=False)
    )
    if updated:
        db.commit()
        logger.info(f"[scheduler] marked {updated} invoice(s) as overdue")
    return updated


def _mark_expiring_locations(db) -> int:
    from app.modules.finance.extended_models import Location

    soon  = datetime.utcnow() + timedelta(days=30)
    today = datetime.utcnow()

    # lease_end within next 30 days → expiring_soon
    expiring = (
        db.query(Location)
        .filter(
            Location.lease_end.isnot(None),
            Location.lease_end > today,
            Location.lease_end <= soon,
            Location.status == "active",
        )
        .update({"status": "expiring_soon"}, synchronize_session=False)
    )

    # lease_end in the past → inactive
    expired = (
        db.query(Location)
        .filter(
            Location.lease_end.isnot(None),
            Location.lease_end < today,
            Location.status.in_(["active", "expiring_soon"]),
        )
        .update({"status": "inactive"}, synchronize_session=False)
    )

    if expiring or expired:
        db.commit()
        logger.info(
            f"[scheduler] locations — {expiring} expiring_soon, {expired} expired → inactive"
        )
    return expiring + expired


def _autogen_reminders(db) -> int:
    """Keep payment (invoice balance) and pickup (arrived shipment) reminders in
    sync with their source records. Idempotent — one reminder per auto_source.

    Backfill guard: an auto reminder created already-past-due (e.g. existing
    overdue invoices on first run) is marked notified so it shows in-app but does
    NOT blast a WhatsApp message. Only reminders that come due *after* creation
    trigger a push."""
    from app.modules.finance.models import Invoice
    from app.modules.cargo.models import Shipment
    from app.modules.customers.models import Customer
    from app.modules.reminders.models import Reminder

    now = datetime.utcnow()
    created = 0
    existing = {
        r.auto_source: r
        for r in db.query(Reminder).filter(Reminder.auto_source.isnot(None)).all()
    }

    # Payment reminders — invoices with an outstanding balance and a due date.
    invoices = (
        db.query(Invoice)
        .filter(Invoice.deleted_at.is_(None), Invoice.due_date.isnot(None))
        .all()
    )
    for inv in invoices:
        key = f"invoice:{inv.id}"
        r = existing.get(key)
        settled = float(inv.balance_due or 0) <= 0 or inv.status in ("paid", "cancelled", "written_off")
        if settled:
            if r and r.status == "pending":
                r.status, r.completed_at = "done", now
            continue
        if r is None:
            bal = float(inv.balance_due or 0)
            cur = inv.currency or "XAF"
            cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
            cname = ((cust.company_name or f"{cust.first_name} {cust.last_name}").strip()) if cust else ""
            db.add(Reminder(
                company_id=inv.company_id or 1,
                title=f"Encaisser {inv.invoice_number} — solde {bal:,.0f} {cur}",
                contact_name=cname or None,
                contact_phone=(cust.phone if cust else None),
                type="payment", due_at=inv.due_date,
                ref_model=inv.ref_model or "invoice", ref_id=inv.ref_id or inv.id,
                customer_id=inv.customer_id, notify_wa=True, auto_source=key,
                notified_at=now if inv.due_date <= now else None,
            ))
            created += 1

    # Pickup reminders — shipments arrived and awaiting warehouse pickup.
    READY = ("arrived_destination", "customs_cleared", "out_for_delivery")
    for s in db.query(Shipment).filter(Shipment.deleted_at.is_(None)).all():
        key = f"pickup:{s.id}"
        r = existing.get(key)
        ready = s.delivery_type == "warehouse_pickup" and s.status in READY
        if s.status == "delivered" or not ready:
            if r and r.status == "pending" and s.status == "delivered":
                r.status, r.completed_at = "done", now
            continue
        if r is None:
            due = s.arrived_at or now
            who = s.receiver_name or "le client"
            addr = ", ".join(p for p in (
                s.receiver_address, s.receiver_quartier, s.receiver_city, s.receiver_country
            ) if p)
            db.add(Reminder(
                company_id=s.company_id or 1,
                title=f"Enlèvement {s.tracking_number or f'#{s.id}'} — prévenir {who}",
                contact_name=s.receiver_name or None,
                contact_phone=s.receiver_phone or None,
                address=addr or None,
                type="pickup", due_at=due,
                ref_model="shipment", ref_id=s.id,
                customer_id=s.customer_id, notify_wa=True, auto_source=key,
                notified_at=now if due <= now else None,
            ))
            created += 1

    db.commit()
    if created:
        logger.info(f"[scheduler] auto-generated {created} reminder(s)")
    return created


def _notify_due_reminders(db) -> int:
    """WhatsApp-push reminders that are due and not yet notified. Best-effort:
    the Cloud API only allows free-form text inside the 24h window, so a failed
    send is logged and the in-app view remains the reliable channel."""
    import os
    from app.modules.reminders.models import Reminder
    from app.modules.whatsapp.whatsapp_client import send_text

    admin_wa = os.getenv("WHATSAPP_ADMIN_NOTIFY_WA_ID", "")
    now = datetime.utcnow()
    due = (
        db.query(Reminder)
        .filter(
            Reminder.status == "pending",
            Reminder.notify_wa.is_(True),
            Reminder.notified_at.is_(None),
            Reminder.due_at <= now,
        )
        .all()
    )
    sent = 0
    for r in due:
        to = r.notify_wa_to or admin_wa
        if not to:
            continue
        icon = {"payment": "💰", "pickup": "📦", "delivery": "🚚"}.get(r.type, "🔔")
        body = f"{icon} Rappel TehTek\n{r.title}"
        contact = " ".join(p for p in (r.contact_name, r.contact_phone) if p)
        if contact:
            body += f"\n👤 {contact}"
        if r.address:
            body += f"\n📍 {r.address}"
        if r.notes:
            body += f"\n{r.notes}"
        try:
            send_text(to, body)
            r.notified_at = now
            sent += 1
        except Exception as e:
            logger.warning(f"[scheduler] reminder WA push failed (id={r.id}): {e}")
    if sent:
        db.commit()
        logger.info(f"[scheduler] pushed {sent} reminder(s) over WhatsApp")
    return sent


def _run_all_jobs():
    db = SessionLocal()
    try:
        _mark_overdue_invoices(db)
        _mark_expiring_locations(db)
        _autogen_reminders(db)
        _notify_due_reminders(db)
    except Exception as e:
        logger.error(f"[scheduler] job error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


# ── Scheduler loop ─────────────────────────────────────────────────────────────

def _loop():
    logger.info("[scheduler] started — interval %ds", _INTERVAL_SECONDS)
    while True:
        _run_all_jobs()
        time.sleep(_INTERVAL_SECONDS)


def start():
    """Start the background scheduler in a daemon thread (called from lifespan)."""
    t = threading.Thread(target=_loop, daemon=True, name="tehtek-scheduler")
    t.start()
    logger.info("[scheduler] daemon thread started")
