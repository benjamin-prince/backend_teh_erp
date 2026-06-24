"""add tax config to orders and service_projects (tax_type, tax_rate, price_inclusive, retenue_amount)

Revision ID: s7j8k9l0m1n2
Revises: r6i7j8k9l0m1
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "s7j8k9l0m1n2"
down_revision = "r6i7j8k9l0m1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("orders", "service_projects"):
        op.add_column(table, sa.Column("retenue_amount", sa.Numeric(14, 2), server_default="0", nullable=False))
        op.add_column(table, sa.Column("tax_type", sa.String(20), server_default="none", nullable=False))
        op.add_column(table, sa.Column("tax_rate", sa.Numeric(6, 3), server_default="0", nullable=False))
        op.add_column(table, sa.Column("price_inclusive", sa.Boolean(), server_default=sa.false(), nullable=False))
    # Backfill: existing rows with TVA already applied → tax_type='tva', rate 19.25
    op.execute("UPDATE orders SET tax_type='tva', tax_rate=19.25 WHERE tax_amount > 0")
    op.execute("UPDATE service_projects SET tax_type='tva', tax_rate=19.25 WHERE tax_amount > 0")


def downgrade() -> None:
    for table in ("service_projects", "orders"):
        op.drop_column(table, "price_inclusive")
        op.drop_column(table, "tax_rate")
        op.drop_column(table, "tax_type")
        op.drop_column(table, "retenue_amount")
