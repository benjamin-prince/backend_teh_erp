"""add money_accounts table

Revision ID: 6205f6379a17
Revises: cae57c24e7f5
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision    = "6205f6379a17"
down_revision = "cae57c24e7f5"   # ← last migration in your versions/ folder
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "money_accounts",
        sa.Column("id",              sa.Integer(),                  primary_key=True),
        sa.Column("company_id",      sa.Integer(),                  sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name",            sa.String(120),                nullable=False),
        sa.Column("account_type",    sa.String(40),                 nullable=False, server_default="cash"),
        sa.Column("currency",        sa.String(10),                 nullable=False, server_default="XAF"),
        sa.Column("opening_balance", sa.Float(),                    nullable=False, server_default="0"),
        sa.Column("balance",         sa.Float(),                    nullable=False, server_default="0"),
        sa.Column("notes",           sa.Text(),                     nullable=True),
        sa.Column("created_by",      sa.Integer(),                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True),    server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True),    nullable=True),
        sa.Column("deleted_at",      sa.DateTime(timezone=True),    nullable=True),
    )


def downgrade() -> None:
    op.drop_table("money_accounts")
