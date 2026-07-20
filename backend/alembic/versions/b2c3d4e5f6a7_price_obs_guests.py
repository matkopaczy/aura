"""price_observations.guests — liczba gości wyszukiwania (pokoje 1-osobowe)

Segmentacja obserwacji po liczbie gości: 2 = domyślny skan (istniejące dane),
1 = osobny lekki przebieg 1-osobowy. Server_default '2' — istniejące wiersze
dostają 2, więc dotychczasowe mediany 2-os. bez zmian.

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-07-20 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'price_observations',
        sa.Column('guests', sa.Integer(), nullable=False, server_default='2'),
    )


def downgrade() -> None:
    op.drop_column('price_observations', 'guests')
