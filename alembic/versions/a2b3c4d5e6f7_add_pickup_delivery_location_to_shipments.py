"""add pickup_location and delivery_location to shipments

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'a2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('shipments', sa.Column('pickup_location',   sa.String(120), nullable=True))
    op.add_column('shipments', sa.Column('delivery_location', sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column('shipments', 'delivery_location')
    op.drop_column('shipments', 'pickup_location')
