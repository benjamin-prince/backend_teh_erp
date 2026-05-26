"""add priority to purchase_commitments

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4b5c6d7e8f9'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'purchase_commitments',
        sa.Column('priority', sa.Integer(), nullable=False, server_default='3'),
    )


def downgrade():
    op.drop_column('purchase_commitments', 'priority')
