"""TEHTEK — Invoice numbering.

Two rules govern the number a source document (service project, order,
shipment…) carries:

SEQ-002 — a number shown to a customer never changes. Regenerating an invoice
used to burn a fresh sequence value, and `next_sequence` stamps the CURRENT
year/month, so the solde of a May project regenerated in August came back as
INV-2026-08-000051 instead of the number already sent out.

SEQ-003 — every invoice of one document shares ONE number. The acompte, the
solde and any intermediate tranche all print INV-2026-05-000018, so the
customer has a single reference per project. `invoices.invoice_number` is
therefore NOT unique (see the SEQ-003 migration); nothing looks an invoice up
by its number, rows are addressed by id.
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


def _reusable_invoice(db: Session, ref_model: Optional[str], ref_id: Optional[int],
                      number: Optional[str]) -> Optional[Invoice]:
    """Most recent discarded, never-paid invoice of that source document.

    Restricted to rows already carrying the document's number: SEQ-002 forbids
    rewriting an issued number, so a legacy row numbered differently must be
    left alone and a fresh row created instead.
    """
    if not ref_model or not ref_id or not number:
        return None
    return (
        db.query(Invoice)
        .filter(
            Invoice.ref_model      == ref_model,
            Invoice.ref_id         == ref_id,
            Invoice.invoice_number == number,
            Invoice.deleted_at.isnot(None),
            func.coalesce(Invoice.paid_amount, 0) == 0,
            ~Invoice.payments.any(),
        )
        .order_by(Invoice.id.desc())
        .first()
    )


def _document_number(db: Session, ref_model: Optional[str],
                     ref_id: Optional[int]) -> Optional[str]:
    """SEQ-003: the number this document already carries, if any.

    The FIRST invoice ever issued for the document sets the number every later
    tranche reuses — including invoices since deleted, so a discarded first
    tranche cannot silently renumber the document.
    """
    if not ref_model or not ref_id:
        return None
    row = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.ref_model == ref_model, Invoice.ref_id == ref_id)
        .order_by(Invoice.id.asc())
        .first()
    )
    return row[0] if row else None


def issue_invoice(db: Session, *, ref_model: Optional[str] = None,
                  ref_id: Optional[int] = None, **fields) -> Invoice:
    """Create an invoice carrying its document's number.

    Reuses the row of a deleted, unpaid invoice for the same
    `(ref_model, ref_id)` when there is one — same number, same id. Otherwise
    creates a row and gives it the number the document already carries
    (SEQ-003), drawing a new sequence value only for a document's first
    invoice. Flushed, not committed: the caller commits.
    """
    number = _document_number(db, ref_model, ref_id)
    inv = _reusable_invoice(db, ref_model, ref_id, number)
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

    if number is None:
        number = next_sequence(db, SequenceType.invoice_number)

    inv = Invoice(
        invoice_number = number,
        ref_model      = ref_model,
        ref_id         = ref_id,
        **fields,
    )
    db.add(inv)
    db.flush()
    return inv
