"""Create media_items table

Revision ID: 1001_create_media_items
Revises: None
Create Date: 2026-07-21 08:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1001_create_media_items'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'media_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('imdb_id', sa.String(length=20), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.Enum('movie', 'series', name='media_type'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('poster_url', sa.String(length=500), nullable=True),
        sa.Column('background_url', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('imdb_id')
    )
    op.create_index(op.f('ix_media_items_imdb_id'), 'media_items', ['imdb_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_media_items_imdb_id'), table_name='media_items')
    op.drop_table('media_items')
