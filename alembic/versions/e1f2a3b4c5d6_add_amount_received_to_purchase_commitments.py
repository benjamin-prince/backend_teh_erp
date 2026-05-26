"""add amount_received to purchase_commitments

Revision ID: e1f2a3b4c5d6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'purchase_commitments',
        sa.Column('amount_received', sa.Float(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('purchase_commitments', 'amount_received')
