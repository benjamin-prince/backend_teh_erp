"""add shop fields to products (is_published, is_featured, compare_price)

Revision ID: e9f0a1b2c3d4
Revises: d7e8f9a0b1c2
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'e9f0a1b2c3d4'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'products',
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'products',
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'products',
        sa.Column('compare_price', sa.Numeric(14, 2), nullable=True),
    )
    # image_url may already exist — add only if missing
    op.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);
    """)


def downgrade():
    op.drop_column('products', 'compare_price')
    op.drop_column('products', 'is_featured')
    op.drop_column('products', 'is_published')
