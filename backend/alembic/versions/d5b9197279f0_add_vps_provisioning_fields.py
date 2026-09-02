"""add vps provisioning fields

Revision ID: d5b9197279f0
Revises: 513209c2dab3
Create Date: 2026-09-02 03:47:11.308905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5b9197279f0'
down_revision: Union[str, Sequence[str], None] = '513209c2dab3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('vps_orders', sa.Column('hostname', sa.String(), nullable=True))
    op.add_column('vps_orders', sa.Column('purchased_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('vps_orders', sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('vps_orders', 'expiry_date')
    op.drop_column('vps_orders', 'purchased_date')
    op.drop_column('vps_orders', 'hostname')
