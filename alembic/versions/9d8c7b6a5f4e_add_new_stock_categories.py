"""add new stock categories: printer, storage, telecom, tv_av

Revision ID: 9d8c7b6a5f4e
Revises: e9f0a1b2c3d4
Create Date: 2026-05-26

"""
from alembic import op

revision = "9d8c7b6a5f4e"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE stockcategory ADD VALUE IF NOT EXISTS 'printer'")
    op.execute("ALTER TYPE stockcategory ADD VALUE IF NOT EXISTS 'storage'")
    op.execute("ALTER TYPE stockcategory ADD VALUE IF NOT EXISTS 'telecom'")
    op.execute("ALTER TYPE stockcategory ADD VALUE IF NOT EXISTS 'tv_av'")


def downgrade() -> None:
    pass
