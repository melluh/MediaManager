"""Create media_watch and tmdb_recommendation_list tables

Users' watch history is synced from the media server, and TMDB's
recommendation lists are stored for building personal recommendations.
Nothing is backfilled: both are filled from their sources by scheduled tasks.

Revision ID: c3d8f1a6b2e9
Revises: e7c2a9d4f1b6
Create Date: 2026-10-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d8f1a6b2e9"
down_revision: Union[str, None] = "e7c2a9d4f1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media_watch",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("server_item_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("imdb_id", sa.String(), nullable=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("tvdb_id", sa.Integer(), nullable=True),
        sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "media_type", "server_item_id"),
    )

    op.create_table(
        "tmdb_recommendation_list",
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("media_type", "tmdb_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("tmdb_recommendation_list")
    op.drop_table("media_watch")
