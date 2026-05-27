"""add debt_type and interest fields to personal_debts

Revision ID: l0c1d2e3f4g5
Revises: k9b0c1d2e3f4
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'l0c1d2e3f4g5'
down_revision = 'k9b0c1d2e3f4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('personal_debts', sa.Column('debt_type',       sa.String(20), nullable=True, server_default='personal'))
    op.add_column('personal_debts', sa.Column('interest_rate',   sa.Float(),    nullable=True))
    op.add_column('personal_debts', sa.Column('interest_period', sa.String(20), nullable=True))
    # backfill existing rows
    op.execute("UPDATE personal_debts SET debt_type = 'personal' WHERE debt_type IS NULL")


def downgrade():
    op.drop_column('personal_debts', 'interest_period')
    op.drop_column('personal_debts', 'interest_rate')
    op.drop_column('personal_debts', 'debt_type')
