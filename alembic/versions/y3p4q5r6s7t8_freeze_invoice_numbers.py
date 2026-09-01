"""SEQ-002: an issued invoice number is immutable

Regenerating an invoice used to draw a fresh sequence value, so a document
already sent to a customer as INV-2026-05-000018 came back as INV-2026-09-xxxxxx.
The application now reuses the number (finance/numbering.issue_invoice); this
trigger makes the rule hold for every writer, raw SQL included.

To correct a number deliberately, drop the trigger, fix the row, recreate it.

Revision ID: y3p4q5r6s7t8
Revises: x2o3p4q5r6s7
Create Date: 2026-09-01
"""
from alembic import op

revision = "y3p4q5r6s7t8"
down_revision = "x2o3p4q5r6s7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION tehtek_freeze_invoice_number()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.invoice_number IS DISTINCT FROM OLD.invoice_number THEN
                RAISE EXCEPTION
                    'SEQ-002: invoice number % is final and cannot become %',
                    OLD.invoice_number, NEW.invoice_number
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_freeze_invoice_number ON invoices")
    op.execute("""
        CREATE TRIGGER trg_freeze_invoice_number
            BEFORE UPDATE OF invoice_number ON invoices
            FOR EACH ROW
            EXECUTE FUNCTION tehtek_freeze_invoice_number();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_freeze_invoice_number ON invoices")
    op.execute("DROP FUNCTION IF EXISTS tehtek_freeze_invoice_number()")
