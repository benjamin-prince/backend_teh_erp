"""add condition column to products

Revision ID: d4e5f6a7b8c9
Revises: c3f5a8b2e1d9
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3f5a8b2e1d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("condition", sa.String(20), nullable=False, server_default="new"),
    )


def downgrade() -> None:
    op.drop_column("products", "condition")
