"""add shipment_items table

Revision ID: a9f3b2c1d4e5
Revises: ed56daa408ae
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9f3b2c1d4e5'
down_revision = 'cae57c24e7f5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shipment_items',
        sa.Column('id',          sa.Integer(),     primary_key=True),
        sa.Column('shipment_id', sa.Integer(),     sa.ForeignKey('shipments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(500),   nullable=False),
        sa.Column('quantity',    sa.Numeric(10,3), nullable=False, server_default='1'),
        sa.Column('unit',        sa.String(30),    nullable=False, server_default='pcs'),
        sa.Column('weight_kg',   sa.Numeric(10,3), nullable=True),
        sa.Column('notes',       sa.Text(),        nullable=True),
        sa.Column('sort_order',  sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('created_at',  sa.DateTime(),    nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_shipment_items_shipment_id', 'shipment_items', ['shipment_id'])


def downgrade():
    op.drop_index('ix_shipment_items_shipment_id')
    op.drop_table('shipment_items')
