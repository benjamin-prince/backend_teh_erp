"""add company document info fields (address, phone, fax, nui, rccm, email, website)

Revision ID: r6i7j8k9l0m1
Revises: q5h6i7j8k9l0
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "r6i7j8k9l0m1"
down_revision = "q5h6i7j8k9l0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("phone", sa.String(60), nullable=True))
    op.add_column("companies", sa.Column("fax", sa.String(60), nullable=True))
    op.add_column("companies", sa.Column("nui", sa.String(50), nullable=True))
    op.add_column("companies", sa.Column("rccm", sa.String(50), nullable=True))
    op.add_column("companies", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("website", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "website")
    op.drop_column("companies", "email")
    op.drop_column("companies", "rccm")
    op.drop_column("companies", "nui")
    op.drop_column("companies", "fax")
    op.drop_column("companies", "phone")
    op.drop_column("companies", "address")
