"""add ref_model and ref_id to expenses

Revision ID: q5h6i7j8k9l0
Revises: o3f4g5h6i7j8
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "q5h6i7j8k9l0"
down_revision = "o3f4g5h6i7j8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("ref_model", sa.String(100), nullable=True))
    op.add_column("expenses", sa.Column("ref_id", sa.Integer(), nullable=True))
    op.add_column("expenses", sa.Column("currency", sa.String(10), nullable=True, server_default="XAF"))


def downgrade() -> None:
    op.drop_column("expenses", "ref_model")
    op.drop_column("expenses", "ref_id")
    op.drop_column("expenses", "currency")
