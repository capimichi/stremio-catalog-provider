"""Create file_mappings table

Revision ID: 1004_create_file_mappings
Revises: 1003_create_episodes
Create Date: 2026-07-21 08:03:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1004_create_file_mappings'
down_revision: Union[str, Sequence[str], None] = '1003_create_episodes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'file_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('torrent_hash', sa.String(length=40), nullable=False),
        sa.Column('file_index', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('media_item_id', sa.Integer(), nullable=True),
        sa.Column('episode_id', sa.Integer(), nullable=True),
        sa.Column('manually_corrected', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['media_item_id'], ['media_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['torrent_hash'], ['torrents.info_hash'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('file_mappings')
