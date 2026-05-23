"""shipment_item car fields and photos

Revision ID: c4d7e8f10b21
Revises: 6205f6379a17
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c4d7e8f10b21'
down_revision = '6205f6379a17'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shipment_items', sa.Column('is_car',       sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('shipment_items', sa.Column('vin',          sa.String(50),  nullable=True))
    op.add_column('shipment_items', sa.Column('make',         sa.String(80),  nullable=True))
    op.add_column('shipment_items', sa.Column('model',        sa.String(80),  nullable=True))
    op.add_column('shipment_items', sa.Column('year',         sa.Integer(),   nullable=True))
    op.add_column('shipment_items', sa.Column('color',        sa.String(50),  nullable=True))
    op.add_column('shipment_items', sa.Column('mileage_km',   sa.Integer(),   nullable=True))
    op.add_column('shipment_items', sa.Column('engine',       sa.String(80),  nullable=True))
    op.add_column('shipment_items', sa.Column('transmission', sa.String(30),  nullable=True))
    op.add_column('shipment_items', sa.Column('fuel_type',    sa.String(30),  nullable=True))
    op.add_column('shipment_items', sa.Column('title_ready',  sa.Boolean(),   nullable=True))
    op.add_column('shipment_items', sa.Column('no_lien',      sa.Boolean(),   nullable=True))
    op.add_column('shipment_items', sa.Column('is_drivable',  sa.Boolean(),   nullable=True))
    op.add_column('shipment_items', sa.Column('options_text', sa.Text(),      nullable=True))
    op.add_column('shipment_items', sa.Column('photos',       postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.create_index('ix_shipment_items_vin', 'shipment_items', ['vin'])


def downgrade():
    op.drop_index('ix_shipment_items_vin', table_name='shipment_items')
    for col in (
        'photos', 'options_text', 'is_drivable', 'no_lien', 'title_ready',
        'fuel_type', 'transmission', 'engine', 'mileage_km', 'color',
        'year', 'model', 'make', 'vin', 'is_car',
    ):
        op.drop_column('shipment_items', col)
