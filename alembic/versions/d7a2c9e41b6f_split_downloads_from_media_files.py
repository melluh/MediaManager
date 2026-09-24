"""Split downloads from media files, drop quality columns, store file probes

A movie_file/episode_file row used to be created as soon as a download
started, doubling as the link between the torrent and its media. Those links
now live in their own tables (movie_download, episode_download), and a file
row only exists once its file is actually in the library - so relative_path
becomes NOT NULL, and the rows still waiting for a download are dropped (their
link rows carry them instead).

The title-derived `quality` columns go away: a file's quality is now probed
from the file itself, stored alongside the rest of its probe in `details`.
Torrents instead record the quality slot they were downloaded for, left NULL
for existing torrents since nothing reliably recorded it.

Revision ID: d7a2c9e41b6f
Revises: b4c1e7d92a3f
Create Date: 2026-09-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7a2c9e41b6f"
down_revision: Union[str, None] = "b4c1e7d92a3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_QUALITY_TABLES = ("movie_file", "episode_file", "torrent", "indexer_query_result")


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("torrent", sa.Column("slot", sa.String(), nullable=True))

    op.create_table(
        "movie_download",
        sa.Column("torrent_id", sa.UUID(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("file_path_suffix", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["torrent_id"], ["torrent.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("torrent_id", "movie_id"),
    )
    op.create_index(
        op.f("ix_movie_download_movie_id"), "movie_download", ["movie_id"]
    )
    op.create_table(
        "episode_download",
        sa.Column("torrent_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("file_path_suffix", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["torrent_id"], ["torrent.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["episode_id"], ["episode.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("torrent_id", "episode_id"),
    )
    op.create_index(
        op.f("ix_episode_download_episode_id"), "episode_download", ["episode_id"]
    )

    # Every torrent keeps its link to the media it was downloaded for, imported
    # or not - the media detail pages list torrents through these links.
    op.execute(
        """
        INSERT INTO movie_download (torrent_id, movie_id, file_path_suffix)
        SELECT torrent_id, movie_id, file_path_suffix FROM movie_file
        WHERE torrent_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO episode_download (torrent_id, episode_id, file_path_suffix)
        SELECT torrent_id, episode_id, file_path_suffix FROM episode_file
        WHERE torrent_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # A row with no path is either a download that hasn't been imported (now
    # carried by its link row) or a file the library scan couldn't find. A
    # file that is on disk after all gets re-adopted by the next library scan.
    for table in ("movie_file", "episode_file"):
        op.execute(f"DELETE FROM {table} WHERE relative_path IS NULL")  # noqa: S608
        op.alter_column(table, "relative_path", nullable=False)
        op.add_column(
            table,
            sa.Column(
                "details", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
        )
        op.add_column(table, sa.Column("probed_mtime_ns", sa.BigInteger(), nullable=True))

    for table in _QUALITY_TABLES:
        op.drop_column(table, "quality")
    op.execute("DROP TYPE IF EXISTS quality")


def downgrade() -> None:
    """Downgrade schema."""
    quality = postgresql.ENUM(
        "uhd", "fullhd", "hd", "sd", "unknown", name="quality", create_type=False
    )
    quality.create(op.get_bind(), checkfirst=True)
    for table in _QUALITY_TABLES:
        op.add_column(
            table,
            sa.Column("quality", quality, nullable=False, server_default="unknown"),
        )

    for table in ("movie_file", "episode_file"):
        op.drop_column(table, "probed_mtime_ns")
        op.drop_column(table, "details")
        op.alter_column(table, "relative_path", nullable=True)

    # Downloads not imported yet go back to being path-less file rows.
    op.execute(
        """
        INSERT INTO movie_file (movie_id, file_path_suffix, torrent_id, quality)
        SELECT d.movie_id, d.file_path_suffix, d.torrent_id, 'unknown'
        FROM movie_download d JOIN torrent t ON t.id = d.torrent_id
        WHERE NOT t.imported
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO episode_file (episode_id, file_path_suffix, torrent_id, quality)
        SELECT d.episode_id, d.file_path_suffix, d.torrent_id, 'unknown'
        FROM episode_download d JOIN torrent t ON t.id = d.torrent_id
        WHERE NOT t.imported
        ON CONFLICT DO NOTHING
        """
    )

    op.drop_index(op.f("ix_episode_download_episode_id"), table_name="episode_download")
    op.drop_table("episode_download")
    op.drop_index(op.f("ix_movie_download_movie_id"), table_name="movie_download")
    op.drop_table("movie_download")
    op.drop_column("torrent", "slot")
