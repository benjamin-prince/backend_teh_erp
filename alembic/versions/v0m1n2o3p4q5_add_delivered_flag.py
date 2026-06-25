"""add delivered flag (independent fulfilment) to orders and service_projects

Revision ID: v0m1n2o3p4q5
Revises: u9l0m1n2o3p4
Create Date: 2026-06-25

Idempotent: uses ADD COLUMN IF NOT EXISTS because some environments already
carry a legacy `orders.delivered_at` column (a plain add_column would abort the
whole transactional migration on that pre-existing column).
"""
from alembic import op

revision = "v0m1n2o3p4q5"
down_revision = "u9l0m1n2o3p4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("orders", "service_projects"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS delivered BOOLEAN NOT NULL DEFAULT FALSE")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP")
        # Backfill: rows already at the legacy "delivered" status are delivered
        op.execute(
            f"UPDATE {table} SET delivered = TRUE, "
            f"delivered_at = COALESCE(delivered_at, updated_at, created_at) "
            f"WHERE status = 'delivered'"
        )


def downgrade() -> None:
    for table in ("service_projects", "orders"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS delivered_at")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS delivered")
