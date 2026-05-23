"""cargo_routes and cargo_route_stops tables; add cargo_route_id to shipments.

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cargo_routes",
        sa.Column("id",             sa.Integer(), nullable=False),
        sa.Column("company_id",     sa.Integer(), nullable=False),
        sa.Column("name",           sa.String(150), nullable=False),
        sa.Column("code",           sa.String(50),  nullable=False),
        sa.Column("origin_country", sa.String(100), nullable=False),
        sa.Column("dest_country",   sa.String(100), nullable=False),
        sa.Column("transport_mode", sa.String(20),  nullable=False),
        sa.Column("is_active",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("notes",          sa.Text(),      nullable=True),
        sa.Column("created_at",     sa.DateTime(),  nullable=False),
        sa.Column("updated_at",     sa.DateTime(),  nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cargo_routes_company", "cargo_routes", ["company_id"])

    op.create_table(
        "cargo_route_stops",
        sa.Column("id",             sa.Integer(), nullable=False),
        sa.Column("route_id",       sa.Integer(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("location_id",    sa.Integer(), nullable=True),
        sa.Column("event_type",     sa.String(50),  nullable=False),
        sa.Column("label",          sa.String(150), nullable=True),
        sa.Column("stop_side",      sa.String(20),  nullable=False, server_default="origin"),
        sa.Column("condition",      sa.String(50),  nullable=True),
        sa.ForeignKeyConstraint(["route_id"],    ["cargo_routes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cargo_route_stops_route", "cargo_route_stops", ["route_id"])

    op.add_column("shipments", sa.Column(
        "cargo_route_id", sa.Integer(), nullable=True
    ))
    op.create_foreign_key(
        "fk_shipments_cargo_route",
        "shipments", "cargo_routes",
        ["cargo_route_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_shipments_cargo_route", "shipments", type_="foreignkey")
    op.drop_column("shipments", "cargo_route_id")
    op.drop_index("ix_cargo_route_stops_route", "cargo_route_stops")
    op.drop_table("cargo_route_stops")
    op.drop_index("ix_cargo_routes_company", "cargo_routes")
    op.drop_table("cargo_routes")
