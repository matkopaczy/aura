"""user is_curator

Revision ID: 0a79891989aa
Revises: e9c194e896d9
Create Date: 2026-07-16 12:07:05.684482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0a79891989aa'
down_revision: Union[str, None] = 'e9c194e896d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_curator', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_curator')
