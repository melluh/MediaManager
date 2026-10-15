"""Create media_rating and rating_prompt_dismissal tables

Users can rate movies and shows, and are asked on the dashboard whether they
enjoyed movies they recently watched. Nothing is backfilled: there are no
past opinions to fill it from.

Revision ID: e7c2a9d4f1b6
Revises: b5d2e8f4a1c7
Create Date: 2026-10-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7c2a9d4f1b6"
down_revision: Union[str, None] = "b5d2e8f4a1c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media_rating",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=True),
        sa.Column("show_id", sa.UUID(), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["show_id"], ["show.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "movie_id"),
        sa.UniqueConstraint("user_id", "show_id"),
        sa.CheckConstraint(
            "(movie_id IS NULL) <> (show_id IS NULL)",
            name="media_rating_one_media",
        ),
        sa.CheckConstraint(
            "score BETWEEN -2 AND 2", name="media_rating_score_range"
        ),
    )
    op.create_index(
        op.f("ix_media_rating_user_id"), "media_rating", ["user_id"]
    )

    op.create_table(
        "rating_prompt_dismissal",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "movie_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("rating_prompt_dismissal")
    op.drop_index(op.f("ix_media_rating_user_id"), table_name="media_rating")
    op.drop_table("media_rating")
