"""add personal credit cards and loans

Revision ID: n2e3f4g5h6i7
Revises: m1d2e3f4g5h6
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "n2e3f4g5h6i7"
down_revision = "m1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "personal_credit_cards",
        sa.Column("id",                sa.Integer(),    primary_key=True, index=True),
        sa.Column("bank_name",         sa.String(200),  nullable=False),
        sa.Column("card_name",         sa.String(200),  nullable=False),
        sa.Column("last_four",         sa.String(4),    nullable=True),
        sa.Column("credit_limit",      sa.Float(),      nullable=False),
        sa.Column("current_balance",   sa.Float(),      nullable=False, server_default="0"),
        sa.Column("apr",               sa.Float(),      nullable=True),
        sa.Column("min_payment_pct",   sa.Float(),      nullable=True),   # % of balance
        sa.Column("min_payment_fixed", sa.Float(),      nullable=True),   # fixed amount
        sa.Column("statement_day",     sa.Integer(),    nullable=True),   # day of month
        sa.Column("due_day",           sa.Integer(),    nullable=True),   # day of month
        sa.Column("currency",          sa.String(10),   nullable=False, server_default="XAF"),
        sa.Column("status",            sa.String(20),   nullable=False, server_default="active"),
        sa.Column("notes",             sa.Text(),       nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "personal_credit_card_payments",
        sa.Column("id",           sa.Integer(),  primary_key=True, index=True),
        sa.Column("card_id",      sa.Integer(),  sa.ForeignKey("personal_credit_cards.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount",       sa.Float(),    nullable=False),
        sa.Column("currency",     sa.String(10), nullable=False, server_default="XAF"),
        sa.Column("payment_date", sa.Date(),     nullable=False),
        sa.Column("notes",        sa.Text(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "personal_loans",
        sa.Column("id",              sa.Integer(),   primary_key=True, index=True),
        sa.Column("lender_name",     sa.String(200), nullable=False),
        sa.Column("loan_type",       sa.String(30),  nullable=False, server_default="bank"),
        sa.Column("original_amount", sa.Float(),     nullable=False),
        sa.Column("current_balance", sa.Float(),     nullable=False),
        sa.Column("monthly_payment", sa.Float(),     nullable=True),
        sa.Column("interest_rate",   sa.Float(),     nullable=True),
        sa.Column("start_date",      sa.Date(),      nullable=False),
        sa.Column("maturity_date",   sa.Date(),      nullable=True),
        sa.Column("payment_day",     sa.Integer(),   nullable=True),   # day of month
        sa.Column("currency",        sa.String(10),  nullable=False, server_default="XAF"),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="current"),
        sa.Column("notes",           sa.Text(),      nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "personal_loan_payments",
        sa.Column("id",           sa.Integer(),  primary_key=True, index=True),
        sa.Column("loan_id",      sa.Integer(),  sa.ForeignKey("personal_loans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount",       sa.Float(),    nullable=False),
        sa.Column("currency",     sa.String(10), nullable=False, server_default="XAF"),
        sa.Column("payment_date", sa.Date(),     nullable=False),
        sa.Column("notes",        sa.Text(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("personal_loan_payments")
    op.drop_table("personal_loans")
    op.drop_table("personal_credit_card_payments")
    op.drop_table("personal_credit_cards")
