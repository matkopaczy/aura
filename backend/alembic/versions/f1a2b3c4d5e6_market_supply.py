"""market supply snapshots (A5 — podaż rynku, §5.1)

Migawki liczby ofert w rynku (nagłówek "znaleziono N obiektów"), per przebieg
scrapera. Dane rynkowe globalne (bez account_id) — jak floor_signals.

Revision ID: f1a2b3c4d5e6
Revises: d2b3c4e5f6a7
Create Date: 2026-07-19 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'd2b3c4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'market_supply',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
                  autoincrement=True, nullable=False),
        sa.Column('market_id', sa.Uuid(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('total_listings', sa.Integer(), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['market_id'], ['markets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_supply_market_observed', 'market_supply',
                    ['market_id', 'observed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_supply_market_observed', table_name='market_supply')
    op.drop_table('market_supply')
