"""add cargo_route_id to containers

Revision ID: o3f4g5h6i7j8
Revises: n2e3f4g5h6i7
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "o3f4g5h6i7j8"
down_revision = "n2e3f4g5h6i7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "containers",
        sa.Column("cargo_route_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_containers_cargo_route_id",
        "containers",
        "cargo_routes",
        ["cargo_route_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_containers_cargo_route_id", "containers", type_="foreignkey")
    op.drop_column("containers", "cargo_route_id")
