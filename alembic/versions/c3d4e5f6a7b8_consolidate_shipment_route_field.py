"""consolidate shipment route field — migrate route string to cargo_route_id

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-24

For each shipment that has cargo_route_id IS NULL but route IS NOT NULL,
try to match the route string against cargo_routes.name (case-insensitive).
After backfill: rename old 'route' column to 'route_legacy' so data is preserved
but the field is no longer the primary source of truth.

down_revision is b2c3d4e5f6a7 (the merge + currency migration).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Backfill cargo_route_id where route string matches a cargo_route name
    conn.execute(text("""
        UPDATE shipments s
        SET cargo_route_id = cr.id
        FROM cargo_routes cr
        WHERE s.cargo_route_id IS NULL
          AND s.deleted_at IS NULL
          AND cr.deleted_at IS NULL
          AND LOWER(TRIM(s.route)) = LOWER(TRIM(cr.name))
    """))

    # Rename old free-text route column to route_legacy (keeps data, removes confusion)
    op.alter_column('shipments', 'route', new_column_name='route_legacy')


def downgrade():
    op.alter_column('shipments', 'route_legacy', new_column_name='route')
