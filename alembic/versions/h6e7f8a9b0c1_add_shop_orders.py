"""Add shop_orders table and shop_order_number sequence

Revision ID: h6e7f8a9b0c1
Revises: f3b4c5d6e7a8
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision     = 'h6e7f8a9b0c1'
down_revision = 'f3b4c5d6e7a8'
branch_labels = None
depends_on    = None


def upgrade():
    op.create_table(
        "shop_orders",
        sa.Column("id",               sa.Integer,      primary_key=True),
        sa.Column("order_ref",        sa.String(30),   nullable=False, unique=True),
        sa.Column("customer_name",    sa.String(200),  nullable=False),
        sa.Column("customer_phone",   sa.String(30),   nullable=False),
        sa.Column("customer_email",   sa.String(255),  nullable=True),
        sa.Column("customer_city",    sa.String(100),  nullable=True),
        sa.Column("delivery_address", sa.Text,         nullable=True),
        sa.Column("delivery_notes",   sa.Text,         nullable=True),
        sa.Column("items_json",       sa.Text,         nullable=False),
        sa.Column("subtotal",         sa.Numeric(14,2), nullable=False),
        sa.Column("payment_method",   sa.String(30),   nullable=False),
        sa.Column("payment_status",   sa.String(30),   nullable=False, server_default="pending"),
        sa.Column("payment_ref",      sa.String(200),  nullable=True),
        sa.Column("payment_amount",   sa.Numeric(14,2), nullable=True),
        sa.Column("status",           sa.String(30),   nullable=False, server_default="pending"),
        sa.Column("cod_customer_id",  sa.Integer,      nullable=True),
        sa.Column("created_at",       sa.DateTime,     server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",       sa.DateTime,     server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shop_orders_order_ref",      "shop_orders", ["order_ref"])
    op.create_index("ix_shop_orders_payment_ref",    "shop_orders", ["payment_ref"])
    op.create_index("ix_shop_orders_customer_phone", "shop_orders", ["customer_phone"])

    # Seed the sequence row (seed_sequences is idempotent but only runs at app startup)
    seq_table = sa.table(
        "sequence_registry",
        sa.column("sequence_type"), sa.column("prefix"), sa.column("pad_length"),
        sa.column("year_scoped"), sa.column("month_scoped"), sa.column("route_scoped"),
        sa.column("current_value"),
    )
    op.bulk_insert(seq_table, [{
        "sequence_type":  "shop_order_number",
        "prefix":         "SHOP",
        "pad_length":     6,
        "year_scoped":    True,
        "month_scoped":   False,
        "route_scoped":   False,
        "current_value":  0,
    }])


def downgrade():
    op.drop_table("shop_orders")
    op.execute("DELETE FROM sequence_registry WHERE sequence_type = 'shop_order_number'")
