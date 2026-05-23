"""add currency to locations

Revision ID: b2c3d4e5f6a7
Revises: a2b3c4d5e6f7, a3b4c5d6e7f8
Create Date: 2026-05-23

Merges the pickup/delivery locations branch and the cargo routes branch,
then adds currency column to the locations table.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = ('a2b3c4d5e6f7', 'a3b4c5d6e7f8')
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'locations',
        sa.Column('currency', sa.String(10), nullable=False, server_default='XAF')
    )


def downgrade():
    op.drop_column('locations', 'currency')
