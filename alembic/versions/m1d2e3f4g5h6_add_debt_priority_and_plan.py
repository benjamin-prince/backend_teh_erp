"""add debt priority and payment plan fields

Revision ID: m1d2e3f4g5h6
Revises: l0c1d2e3f4g5
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "m1d2e3f4g5h6"
down_revision = "l0c1d2e3f4g5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("personal_debts", sa.Column("priority",        sa.Integer(),    nullable=True))
    op.add_column("personal_debts", sa.Column("plan_amount",     sa.Float(),      nullable=True))
    op.add_column("personal_debts", sa.Column("plan_frequency",  sa.String(20),   nullable=True))
    op.add_column("personal_debts", sa.Column("plan_start_date", sa.Date(),       nullable=True))
    op.add_column("personal_debts", sa.Column("plan_notes",      sa.Text(),       nullable=True))


def downgrade():
    op.drop_column("personal_debts", "plan_notes")
    op.drop_column("personal_debts", "plan_start_date")
    op.drop_column("personal_debts", "plan_frequency")
    op.drop_column("personal_debts", "plan_amount")
    op.drop_column("personal_debts", "priority")
