"""add flat_rate and flat_rate_currency to shipments

Revision ID: n2e3f4g5h6i7
Revises: m1d2e3f4g5h6
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = "n2e3f4g5h6i7"
down_revision = "m1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("shipments", sa.Column("flat_rate", sa.Numeric(14, 2), nullable=True))
    op.add_column("shipments", sa.Column("flat_rate_currency", sa.String(10), nullable=True))


def downgrade():
    op.drop_column("shipments", "flat_rate_currency")
    op.drop_column("shipments", "flat_rate")
