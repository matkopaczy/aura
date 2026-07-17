"""recommendation competitor_median

Revision ID: c1a2b3d4e5f6
Revises: bf74eaa0a9b8
Create Date: 2026-07-17 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'bf74eaa0a9b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mediana konkurencji w momencie rekomendacji — pod licznik konserwatywny (§3.4, §6.3).
    # NULL dla istniejących rekomendacji (brak danych historycznych = nie liczymy ich
    # w wariancie konserwatywnym, zgodnie z zasadą najostrożniejszej atrybucji).
    op.add_column(
        'recommendations',
        sa.Column('competitor_median', sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('recommendations', 'competitor_median')
