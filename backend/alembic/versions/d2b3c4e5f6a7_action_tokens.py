"""action tokens + decision channel

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-07-17 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2b3c4e5f6a7'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kanał decyzji (§6.3): panel czy e-mail. NULL dla decyzji sprzed tej zmiany.
    op.add_column(
        'recommendations',
        sa.Column(
            'decision_channel',
            sa.Enum('DASHBOARD', 'EMAIL', name='decisionchannel', native_enum=False, length=20),
            nullable=True,
        ),
    )
    # Jednorazowe, wygasające tokeny decyzji z e-maila (§8.2, §9).
    op.create_table(
        'action_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('recommendation_id', sa.Uuid(), nullable=False),
        sa.Column(
            'action',
            sa.Enum('ACCEPT', 'REJECT', name='actiontokenaction', native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_action_tokens_account_id', 'action_tokens', ['account_id'])
    op.create_index(
        'ix_action_tokens_recommendation_id', 'action_tokens', ['recommendation_id']
    )
    op.create_index(
        'ix_action_tokens_token_hash', 'action_tokens', ['token_hash'], unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_action_tokens_token_hash', table_name='action_tokens')
    op.drop_index('ix_action_tokens_recommendation_id', table_name='action_tokens')
    op.drop_index('ix_action_tokens_account_id', table_name='action_tokens')
    op.drop_table('action_tokens')
    op.drop_column('recommendations', 'decision_channel')
