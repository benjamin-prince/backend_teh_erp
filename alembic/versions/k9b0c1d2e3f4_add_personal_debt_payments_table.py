"""add personal_debt_payments table

Revision ID: k9b0c1d2e3f4
Revises: j8a9b0c1d2e3
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'k9b0c1d2e3f4'
down_revision = 'j8a9b0c1d2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'personal_debt_payments',
        sa.Column('id',           sa.Integer(),     nullable=False),
        sa.Column('debt_id',      sa.Integer(),     nullable=False),
        sa.Column('amount',       sa.Float(),       nullable=False),
        sa.Column('currency',     sa.String(10),    nullable=False),
        sa.Column('payment_date', sa.Date(),        nullable=False),
        sa.Column('notes',        sa.Text(),        nullable=True),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['debt_id'], ['personal_debts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personal_debt_payments_id',      'personal_debt_payments', ['id'])
    op.create_index('ix_personal_debt_payments_debt_id', 'personal_debt_payments', ['debt_id'])


def downgrade():
    op.drop_index('ix_personal_debt_payments_debt_id', table_name='personal_debt_payments')
    op.drop_index('ix_personal_debt_payments_id',      table_name='personal_debt_payments')
    op.drop_table('personal_debt_payments')
