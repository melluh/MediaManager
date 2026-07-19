"""Add indexes to TV models

Revision ID: 0f1f4b5c2d3e
Revises: 93fb07842385
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f1f4b5c2d3e"
down_revision: Union[str, None] = "e60ae827ed98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_show_external_id"), "show", ["external_id"], unique=False)
    op.create_index(op.f("ix_movie_external_id"), "movie", ["external_id"], unique=False)
    op.create_index(op.f("ix_season_show_id"), "season", ["show_id"], unique=False)
    op.create_index(op.f("ix_episode_season_id"), "episode", ["season_id"], unique=False)
    op.create_index(op.f("ix_episode_file_episode_id"), "episode_file", ["episode_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_episode_file_episode_id"), table_name="episode_file")
    op.drop_index(op.f("ix_episode_season_id"), table_name="episode")
    op.drop_index(op.f("ix_season_show_id"), table_name="season")
    op.drop_index(op.f("ix_movie_external_id"), table_name="movie")
    op.drop_index(op.f("ix_show_external_id"), table_name="show")
