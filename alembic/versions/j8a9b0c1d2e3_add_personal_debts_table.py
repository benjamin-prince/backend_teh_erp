"""add personal_debts table

Revision ID: j8a9b0c1d2e3
Revises: i7f8a9b0c1d2
Create Date: 2026-05-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'j8a9b0c1d2e3'
down_revision = 'i7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'personal_debts',
        sa.Column('id',            sa.Integer(),     primary_key=True, index=True),
        sa.Column('creditor',      sa.String(200),   nullable=False),
        sa.Column('amount',        sa.Float(),       nullable=False),
        sa.Column('currency',      sa.String(10),    nullable=False, server_default='XAF'),
        sa.Column('reason',        sa.String(500),   nullable=True),
        sa.Column('borrowed_date', sa.Date(),        nullable=False),
        sa.Column('due_date',      sa.Date(),        nullable=True),
        sa.Column('is_paid',       sa.Boolean(),     nullable=False, server_default='false'),
        sa.Column('paid_date',     sa.Date(),        nullable=True),
        sa.Column('notes',         sa.Text(),        nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',    sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )


def downgrade():
    op.drop_table('personal_debts')
