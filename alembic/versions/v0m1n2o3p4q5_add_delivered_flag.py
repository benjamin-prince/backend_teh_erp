"""add delivered flag (independent fulfilment) to orders and service_projects

Revision ID: v0m1n2o3p4q5
Revises: u9l0m1n2o3p4
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = "v0m1n2o3p4q5"
down_revision = "u9l0m1n2o3p4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("orders", "service_projects"):
        op.add_column(table, sa.Column("delivered", sa.Boolean(), server_default=sa.false(), nullable=False))
        op.add_column(table, sa.Column("delivered_at", sa.DateTime(), nullable=True))
        # Backfill: rows already at the legacy "delivered" status are delivered
        op.execute(f"UPDATE {table} SET delivered = TRUE, delivered_at = COALESCE(updated_at, created_at) WHERE status = 'delivered'")


def downgrade() -> None:
    for table in ("service_projects", "orders"):
        op.drop_column(table, "delivered_at")
        op.drop_column(table, "delivered")
