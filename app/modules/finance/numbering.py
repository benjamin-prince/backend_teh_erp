"""TEHTEK — Invoice numbering.

SEQ-002: an invoice number, once shown to a customer, never changes.

Regenerating the invoice of a source document (service project, order,
shipment…) used to burn a fresh sequence value, so a customer who had already
received INV-2026-09-000019 got INV-2026-09-000020 for the same document. Here
we reuse the discarded invoice's row — and therefore its number — as long as it
was never paid. A paid or partially paid invoice is never touched: those keep
their number and a new tranche gets its own.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import InvoiceStatus, SequenceType
from app.modules.finance.models import Invoice

# Content fields wiped before a reused row is refilled, so nothing leaks from
# the discarded version of the invoice. `invoice_number`, `id`, `company_id`
# and `invoice_type` are deliberately absent: they belong to the same source
# document and must survive the reuse.
_RESET = {
    "branch_id":            None,
    "status":               InvoiceStatus.draft,
    "customer_id":          None,
    "supplier_id":          None,
    "line_items_json":      None,
    "subtotal":             0,
    "tax_amount":           0,
    "retenue_amount":       0,
    "discount_amount":      0,
    "total":                0,
    "paid_amount":          0,
    "balance_due":          0,
    "tax_type":             "none",
    "tax_rate":             0,
    "advance_pct":          None,
    "guarantee_value":      None,
    "guarantee_unit":       None,
    "delivery_delay_value": None,
    "delivery_delay_unit":  None,
    "currency":             "XAF",
    "due_date":             None,
    "sent_at":              None,
    "paid_at":              None,
    "cancelled_at":         None,
    "cancel_reason":        None,
    "notes":                None,
    "created_by":           None,
    "deleted_at":           None,
}


def _reusable_invoice(db: Session, ref_model: Optional[str],
                      ref_id: Optional[int]) -> Optional[Invoice]:
    """Most recent discarded, never-paid invoice of that source document."""
    if not ref_model or not ref_id:
        return None
    return (
        db.query(Invoice)
        .filter(
            Invoice.ref_model == ref_model,
            Invoice.ref_id    == ref_id,
            Invoice.deleted_at.isnot(None),
            func.coalesce(Invoice.paid_amount, 0) == 0,
            ~Invoice.payments.any(),
        )
        .order_by(Invoice.id.desc())
        .first()
    )


def issue_invoice(db: Session, *, ref_model: Optional[str] = None,
                  ref_id: Optional[int] = None, **fields) -> Invoice:
    """Create an invoice, keeping the number already issued for that document.

    Reuses the row of a deleted, unpaid invoice pointing at the same
    `(ref_model, ref_id)` — same number, same id — otherwise draws the next
    sequence value. The invoice is flushed, not committed: the caller commits.
    """
    inv = _reusable_invoice(db, ref_model, ref_id)
    now = datetime.utcnow()

    if inv is not None:
        for column, default in _RESET.items():
            setattr(inv, column, default)
        for column, value in fields.items():
            setattr(inv, column, value)
        inv.ref_model  = ref_model
        inv.ref_id     = ref_id
        inv.created_at = now   # re-issued today; the printed date follows
        inv.updated_at = now
        db.flush()
        return inv

    from app.modules.companies.controller import next_sequence

    inv = Invoice(
        invoice_number = next_sequence(db, SequenceType.invoice_number),
        ref_model      = ref_model,
        ref_id         = ref_id,
        **fields,
    )
    db.add(inv)
    db.flush()
    return inv
