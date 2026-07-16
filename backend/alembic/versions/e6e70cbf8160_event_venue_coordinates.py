"""event venue coordinates

Revision ID: e6e70cbf8160
Revises: bf229bcd9b8b
Create Date: 2026-07-16 17:33:00.426753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6e70cbf8160'
down_revision: Union[str, None] = 'bf229bcd9b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('venue_lat', sa.Numeric(precision=9, scale=6), nullable=True))
    op.add_column('events', sa.Column('venue_lng', sa.Numeric(precision=9, scale=6), nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'venue_lng')
    op.drop_column('events', 'venue_lat')
