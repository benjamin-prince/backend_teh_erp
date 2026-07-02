"""add guarantee + delivery-delay terms to orders, service_projects, invoices

Revision ID: x2o3p4q5r6s7
Revises: w1n2o3p4q5r6
Create Date: 2026-07-02
"""
from alembic import op

revision = "x2o3p4q5r6s7"
down_revision = "w1n2o3p4q5r6"
branch_labels = None
depends_on = None

_COLS = [
    ("guarantee_value", "INTEGER"),
    ("guarantee_unit", "VARCHAR(10)"),
    ("delivery_delay_value", "INTEGER"),
    ("delivery_delay_unit", "VARCHAR(10)"),
]


def upgrade() -> None:
    for table in ("orders", "service_projects", "invoices"):
        for col, typ in _COLS:
            op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}")


def downgrade() -> None:
    for table in ("orders", "service_projects", "invoices"):
        for col, _ in _COLS:
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
