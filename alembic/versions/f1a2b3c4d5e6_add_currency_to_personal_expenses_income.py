"""add currency across personal, orders, infrastructure, commissions

Revision ID: f1a2b3c4d5e6
Revises: d8e2f4a1b760
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'd8e2f4a1b760'
branch_labels = None
depends_on = None


def upgrade():
    # Personal
    op.add_column('personal_expenses', sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))
    op.add_column('personal_income',   sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))

    # Orders
    op.add_column('orders', sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))

    # Infrastructure services
    op.add_column('service_tickets',    sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))
    op.add_column('service_contracts',  sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))
    op.add_column('solar_projects',     sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))
    op.add_column('service_projects',   sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))

    # Commissions
    op.add_column('commissions',         sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'))
    # Rename flat_rate_xaf → flat_rate and add flat_rate_currency
    op.add_column('commission_partners', sa.Column('flat_rate',          sa.Numeric(14, 2), nullable=True))
    op.add_column('commission_partners', sa.Column('flat_rate_currency', sa.String(10),     nullable=False, server_default='XAF'))
    op.execute("UPDATE commission_partners SET flat_rate = flat_rate_xaf WHERE flat_rate_xaf IS NOT NULL")
    op.drop_column('commission_partners', 'flat_rate_xaf')


def downgrade():
    op.drop_column('personal_expenses', 'currency')
    op.drop_column('personal_income',   'currency')
    op.drop_column('orders',            'currency')
    op.drop_column('service_tickets',   'currency')
    op.drop_column('service_contracts', 'currency')
    op.drop_column('solar_projects',    'currency')
    op.drop_column('service_projects',  'currency')
    op.drop_column('commissions',       'currency')
    op.add_column('commission_partners', sa.Column('flat_rate_xaf', sa.Numeric(14, 2), nullable=True))
    op.execute("UPDATE commission_partners SET flat_rate_xaf = flat_rate WHERE flat_rate IS NOT NULL")
    op.drop_column('commission_partners', 'flat_rate')
    op.drop_column('commission_partners', 'flat_rate_currency')
