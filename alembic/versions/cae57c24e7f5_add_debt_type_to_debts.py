"""add debt_type to debts

Revision ID: cae57c24e7f5
Revises: a3f8c2d14e90
Create Date: 2026-05-13 08:36:11.586660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cae57c24e7f5'
down_revision: Union[str, None] = 'a3f8c2d14e90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "debts",
        sa.Column("debt_type", sa.String(20), nullable=False, server_default="loan"),
    )


def downgrade() -> None:
    op.drop_column("debts", "debt_type")
