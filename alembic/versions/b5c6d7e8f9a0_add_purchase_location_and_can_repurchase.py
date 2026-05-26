"""add purchase_location and can_repurchase to purchase_commitments

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'b5c6d7e8f9a0'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'purchase_commitments',
        sa.Column('purchase_location', sa.String(20), nullable=True),
    )
    op.add_column(
        'purchase_commitments',
        sa.Column('can_repurchase', sa.Boolean(), nullable=True),
    )


def downgrade():
    op.drop_column('purchase_commitments', 'can_repurchase')
    op.drop_column('purchase_commitments', 'purchase_location')
