"""Create episodes table

Revision ID: 1003_create_episodes
Revises: 1002_create_torrents
Create Date: 2026-07-21 08:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1003_create_episodes'
down_revision: Union[str, Sequence[str], None] = '1002_create_torrents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'episodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('media_item_id', sa.Integer(), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('episode', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['media_item_id'], ['media_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('episodes')
