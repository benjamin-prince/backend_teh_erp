"""add customer legal fields

Revision ID: ed56daa408ae
Revises: 
Create Date: 2026-05-02 16:58:02.898566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed56daa408ae'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("customers", sa.Column("entity_type", sa.String(length=50), nullable=False, server_default="individual"))
    op.add_column("customers", sa.Column("nui", sa.String(length=100), nullable=True))
    op.add_column("customers", sa.Column("bp", sa.String(length=100), nullable=True))
    op.add_column("customers", sa.Column("fax", sa.String(length=50), nullable=True))
    op.add_column("customers", sa.Column("whatsapp", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("customers", "whatsapp")
    op.drop_column("customers", "fax")
    op.drop_column("customers", "bp")
    op.drop_column("customers", "nui")
    op.drop_column("customers", "entity_type")
