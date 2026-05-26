"""add price_asked to purchase_commitments

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'purchase_commitments',
        sa.Column('price_asked', sa.Float(), nullable=True),
    )


def downgrade():
    op.drop_column('purchase_commitments', 'price_asked')
