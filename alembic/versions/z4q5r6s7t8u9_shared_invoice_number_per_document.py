"""SEQ-003: one invoice number per source document (drop UNIQUE on invoice_number)

Every invoice of a document — acompte, solde, intermediate tranches — now
carries the SAME number, so a customer sees a single reference per project.
That requires dropping the UNIQUE constraint on invoices.invoice_number.

Safe because no code path looks an invoice UP by its number: every backend and
frontend reference is display-only, and Receivable.invoice_number is a
free-text mirror, not a foreign key. A plain index replaces the unique one so
number searches stay fast.

Revision ID: z4q5r6s7t8u9
Revises: y3p4q5r6s7t8
Create Date: 2026-09-01
"""
from alembic import op

revision = "z4q5r6s7t8u9"
down_revision = "y3p4q5r6s7t8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_invoice_number_key"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_invoice_number ON invoices (invoice_number)"
    )


def downgrade() -> None:
    # Only reversible while no two live invoices share a number.
    op.execute("DROP INDEX IF EXISTS ix_invoice_number")
    op.execute(
        "ALTER TABLE invoices ADD CONSTRAINT invoices_invoice_number_key "
        "UNIQUE (invoice_number)"
    )
