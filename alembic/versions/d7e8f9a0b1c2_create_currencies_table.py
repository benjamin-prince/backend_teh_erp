"""create currencies table

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e8f9a0b1c2'
down_revision = 'c6d7e8f9a0b1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'currencies',
        sa.Column('code',        sa.String(10),  nullable=False, primary_key=True),
        sa.Column('name',        sa.String(100), nullable=False),
        sa.Column('symbol',      sa.String(10),  nullable=True),
        sa.Column('rate_to_xaf', sa.Float(),     nullable=False, server_default='1.0'),
        sa.Column('is_active',   sa.Boolean(),   nullable=False, server_default='true'),
        sa.Column('updated_at',  sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Seed the four default currencies
    op.execute("""
        INSERT INTO currencies (code, name, symbol, rate_to_xaf) VALUES
        ('XAF',  'Franc CFA',        'FCFA', 1.0),
        ('EUR',  'Euro',             '€',    655.957),
        ('USD',  'Dollar américain', '$',    600.0),
        ('CNY',  'Yuan chinois',     '¥',    83.0)
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade():
    op.drop_table('currencies')
