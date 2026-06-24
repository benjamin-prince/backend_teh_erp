"""add advance_pct to invoices (acompte / partial invoice support)

Revision ID: u9l0m1n2o3p4
Revises: t8k9l0m1n2o3
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "u9l0m1n2o3p4"
down_revision = "t8k9l0m1n2o3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("advance_pct", sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "advance_pct")
