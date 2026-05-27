"""add image_urls to products

Revision ID: i7f8a9b0c1d2
Revises: h6e7f8a9b0c1
Create Date: 2026-05-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i7f8a9b0c1d2'
down_revision = 'h6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('image_urls', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('products', 'image_urls')
