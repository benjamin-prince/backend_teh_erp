"""add price_currency to purchase_commitments

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'c6d7e8f9a0b1'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'purchase_commitments',
        sa.Column('price_currency', sa.String(10), nullable=True, server_default='XAF'),
    )


def downgrade():
    op.drop_column('purchase_commitments', 'price_currency')
