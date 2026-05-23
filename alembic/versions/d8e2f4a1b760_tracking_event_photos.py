"""tracking_event photos

Revision ID: d8e2f4a1b760
Revises: c4d7e8f10b21
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd8e2f4a1b760'
down_revision = 'c4d7e8f10b21'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tracking_events',
        sa.Column('photos', postgresql.JSONB(),
                  nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade():
    op.drop_column('tracking_events', 'photos')
