"""add tax status fields to invoices (retenue_amount, tax_type, tax_rate)

Revision ID: t8k9l0m1n2o3
Revises: s7j8k9l0m1n2
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "t8k9l0m1n2o3"
down_revision = "s7j8k9l0m1n2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("retenue_amount", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.add_column("invoices", sa.Column("tax_type", sa.String(20), server_default="none", nullable=False))
    op.add_column("invoices", sa.Column("tax_rate", sa.Numeric(6, 3), server_default="0", nullable=False))
    op.execute("UPDATE invoices SET tax_type='tva', tax_rate=19.25 WHERE tax_amount > 0")


def downgrade() -> None:
    op.drop_column("invoices", "tax_rate")
    op.drop_column("invoices", "tax_type")
    op.drop_column("invoices", "retenue_amount")
