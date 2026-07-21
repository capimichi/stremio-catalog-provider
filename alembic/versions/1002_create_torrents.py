"""Create torrents table

Revision ID: 1002_create_torrents
Revises: 1001_create_media_items
Create Date: 2026-07-21 08:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1002_create_torrents'
down_revision: Union[str, Sequence[str], None] = '1001_create_media_items'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'torrents',
        sa.Column('info_hash', sa.String(length=40), nullable=False),
        sa.Column('magnet_url', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'PROCESSING', 'PROCESSED', 'FAILED', name='torrent_status'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('predefined_media_item_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['predefined_media_item_id'], ['media_items.id'], ),
        sa.PrimaryKeyConstraint('info_hash')
    )


def downgrade() -> None:
    op.drop_table('torrents')
