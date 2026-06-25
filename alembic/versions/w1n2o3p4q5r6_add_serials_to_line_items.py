"""add serials (IMEI/SN/MAC) to order_items and service_milestones

Revision ID: w1n2o3p4q5r6
Revises: v0m1n2o3p4q5
Create Date: 2026-06-25
"""
from alembic import op

revision = "w1n2o3p4q5r6"
down_revision = "v0m1n2o3p4q5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS serials TEXT")
    op.execute("ALTER TABLE service_milestones ADD COLUMN IF NOT EXISTS serials TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS serials")
    op.execute("ALTER TABLE service_milestones DROP COLUMN IF EXISTS serials")
