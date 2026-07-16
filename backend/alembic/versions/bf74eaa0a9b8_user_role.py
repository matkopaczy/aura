"""user role

Revision ID: bf74eaa0a9b8
Revises: 2ede1b3cfa07
Create Date: 2026-07-16 22:29:34.297900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bf74eaa0a9b8'
down_revision: Union[str, None] = '2ede1b3cfa07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Istniejący użytkownicy to właściciele swoich kont -> server_default OWNER.
    op.add_column(
        'users',
        sa.Column(
            'role',
            sa.Enum('OWNER', 'RECEPTION', name='userrole', native_enum=False, length=20),
            nullable=False,
            server_default='OWNER',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'role')
