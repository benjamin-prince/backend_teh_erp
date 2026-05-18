"""create debt tables

Revision ID: a3f8c2d14e90
Revises: a1b2c3d4e5f6
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision      = "a3f8c2d14e90"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id",           sa.Integer(),      primary_key=True),
        sa.Column("company_id",   sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("debt_number",  sa.String(30),     unique=True, nullable=False),   # DBT-2026-0001
        sa.Column("creditor_name",sa.String(255),    nullable=False),
        sa.Column("creditor_type",sa.String(50),     nullable=False),
        sa.Column("purpose",      sa.Text(),         nullable=False),
        sa.Column("ref_model",    sa.String(100),    nullable=True),
        sa.Column("ref_id",       sa.Integer(),      nullable=True),
        sa.Column("ref_label",    sa.String(255),    nullable=True),
        sa.Column("principal",          sa.Numeric(15, 2), nullable=False),
        sa.Column("outstanding",        sa.Numeric(15, 2), nullable=False),
        sa.Column("total_paid",         sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("installment_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("interest_rate",      sa.Numeric(5,  2), nullable=True),
        sa.Column("currency",           sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("repayment_frequency",sa.String(50),     nullable=False, server_default="monthly"),
        sa.Column("start_date",         sa.DateTime(),     nullable=False),
        sa.Column("deadline_date",      sa.DateTime(),     nullable=False),
        sa.Column("end_date",           sa.DateTime(),     nullable=True),
        sa.Column("next_due_date",      sa.DateTime(),     nullable=True),
        sa.Column("last_payment_date",  sa.DateTime(),     nullable=True),
        sa.Column("status",    sa.String(50),  nullable=False, server_default="active"),
        sa.Column("notes",     sa.Text(),      nullable=True),
        sa.Column("created_by",sa.Integer(),   nullable=True),
        sa.Column("created_at",sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",sa.DateTime(),  nullable=True),
        sa.Column("deleted_at",sa.DateTime(),  nullable=True),
    )
    op.create_index("ix_debt_company_status",   "debts", ["company_id", "status"])
    op.create_index("ix_debt_next_due_date",    "debts", ["company_id", "next_due_date"])
    op.create_index("ix_debt_deleted_at",       "debts", ["deleted_at"])

    op.create_table(
        "debt_payments",
        sa.Column("id",                 sa.Integer(),      primary_key=True),
        sa.Column("debt_id",            sa.Integer(),      sa.ForeignKey("debts.id"), nullable=False),
        sa.Column("payment_date",       sa.DateTime(),     nullable=False),
        sa.Column("amount",             sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_method",     sa.String(50),     nullable=False, server_default="bank_transfer"),
        sa.Column("money_account_id",   sa.Integer(),      nullable=True),
        sa.Column("money_account_name", sa.String(255),    nullable=True),
        sa.Column("reference",          sa.String(255),    nullable=True),
        sa.Column("notes",              sa.Text(),         nullable=True),
        sa.Column("created_by",         sa.Integer(),      nullable=True),
        sa.Column("created_at",         sa.DateTime(),     nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_debt_payment_debt_id", "debt_payments", ["debt_id"])


def downgrade() -> None:
    op.drop_index("ix_debt_payment_debt_id",  table_name="debt_payments")
    op.drop_table("debt_payments")
    op.drop_index("ix_debt_deleted_at",       table_name="debts")
    op.drop_index("ix_debt_next_due_date",    table_name="debts")
    op.drop_index("ix_debt_company_status",   table_name="debts")
    op.drop_table("debts")
