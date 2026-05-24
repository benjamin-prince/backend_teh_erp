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


def _run_all_jobs():
    db = SessionLocal()
    try:
        _mark_overdue_invoices(db)
        _mark_expiring_locations(db)
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
