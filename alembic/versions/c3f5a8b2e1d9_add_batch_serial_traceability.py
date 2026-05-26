"""add supplier_batches and serial_numbers tables

Revision ID: c3f5a8b2e1d9
Revises: 9d8c7b6a5f4e
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "c3f5a8b2e1d9"
down_revision = "9d8c7b6a5f4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_batches",
        sa.Column("id",            sa.Integer,      primary_key=True),
        sa.Column("batch_number",  sa.String(50),   nullable=False, unique=True),
        sa.Column("product_id",    sa.Integer,      sa.ForeignKey("products.id"),   nullable=False),
        sa.Column("company_id",    sa.Integer,      sa.ForeignKey("companies.id"),  nullable=False),
        sa.Column("supplier_name", sa.String(200),  nullable=True),
        sa.Column("quantity",      sa.Integer,      nullable=False),
        sa.Column("unit_cost",     sa.Numeric(14,2),nullable=True),
        sa.Column("received_date", sa.DateTime,     nullable=False),
        sa.Column("notes",         sa.Text,         nullable=True),
        sa.Column("created_by",    sa.Integer,      nullable=True),
        sa.Column("created_at",    sa.DateTime,     nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at",    sa.DateTime,     nullable=True),
    )
    op.create_index("ix_batch_company_product", "supplier_batches", ["company_id", "product_id"])

    op.create_table(
        "serial_numbers",
        sa.Column("id",            sa.Integer,      primary_key=True),
        sa.Column("serial_number", sa.String(150),  nullable=False, unique=True),
        sa.Column("product_id",    sa.Integer,      sa.ForeignKey("products.id"),          nullable=False),
        sa.Column("batch_id",      sa.Integer,      sa.ForeignKey("supplier_batches.id"),  nullable=True),
        sa.Column("company_id",    sa.Integer,      sa.ForeignKey("companies.id"),         nullable=False),
        sa.Column("is_generated",  sa.Boolean,      nullable=False, server_default="false"),
        sa.Column("status",        sa.String(30),   nullable=False, server_default="in_stock"),
        sa.Column("customer_id",   sa.Integer,      sa.ForeignKey("customers.id"),         nullable=True),
        sa.Column("customer_name", sa.String(200),  nullable=True),
        sa.Column("sold_at",       sa.DateTime,     nullable=True),
        sa.Column("returned_at",   sa.DateTime,     nullable=True),
        sa.Column("return_reason", sa.Text,         nullable=True),
        sa.Column("notes",         sa.Text,         nullable=True),
        sa.Column("created_by",    sa.Integer,      nullable=True),
        sa.Column("created_at",    sa.DateTime,     nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime,     nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at",    sa.DateTime,     nullable=True),
    )
    op.create_index("ix_serial_company",  "serial_numbers", ["company_id"])
    op.create_index("ix_serial_product",  "serial_numbers", ["product_id"])
    op.create_index("ix_serial_status",   "serial_numbers", ["status"])


def downgrade() -> None:
    op.drop_table("serial_numbers")
    op.drop_table("supplier_batches")
