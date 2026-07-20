"""bookings — zrealizowane rezerwacje gospodarza (B, §3.4)

Prywatne dane gospodarza (account_id), per noc, z rzeczywistą ceną sprzedaży.
Fundament pod prawdziwy ADR/RevPAR i uczciwy licznik wyniku.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-07-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bookings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('property_id', sa.Uuid(), nullable=False),
        sa.Column('stay_date', sa.Date(), nullable=False),
        sa.Column('nightly_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.Column('channel',
                  sa.Enum('BOOKING', 'AIRBNB', 'DIRECT', 'OTHER',
                          name='bookingchannel', native_enum=False, length=20),
                  nullable=False),
        sa.Column('reservation_ref', sa.String(length=100), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('property_id', 'stay_date'),
    )
    op.create_index(op.f('ix_bookings_account_id'), 'bookings', ['account_id'], unique=False)
    op.create_index(op.f('ix_bookings_property_id'), 'bookings', ['property_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bookings_property_id'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_account_id'), table_name='bookings')
    op.drop_table('bookings')
