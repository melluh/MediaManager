"""Persist media directory names and media file relative paths

Revision ID: b7e1c4d9a2f5
Revises: c4a6e9f1b3d7
Create Date: 2026-09-02 00:00:00.000000

"""

import re
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1c4d9a2f5"
down_revision: Union[str, None] = "c4a6e9f1b3d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sanitize(name: str) -> str:
    """Reproduce the app's filename sanitiser; this is what produced the on-disk names."""
    return re.sub(r"[<>:\"/\\|?*\x00-\x1f\x7f]", "", name).strip(" .")


def _canonical_directory_name(
    name: str,
    year: Union[int, None],
    provider: str,
    external_id: object,
) -> str:
    sanitized = _sanitize(name)
    year_part = "" if year is None else f" ({year})"
    return f"{sanitized}{year_part} [{provider}id-{external_id}]"


def select_directory_name(
    *,
    name: str,
    year: Union[int, None],
    provider: str,
    external_id: object,
    entries: Union[Sequence[str], None],
    claimed: set[str],
) -> str:
    """Pick the directory name for one media row.

    ``entries`` is the list of directory names present in the parent directory, or
    ``None`` when that listing could not be obtained (see ``_list_directories``).
    ``claimed`` holds the names already taken by earlier rows in the same parent; a
    directory belongs to at most one media item, so claimed names are skipped.

    Returns the canonical name when nothing on disk matches, which is correct: the
    importers create the directory the first time they write into it.
    """
    canonical = _canonical_directory_name(name, year, provider, external_id)
    if entries is None:
        return canonical

    available = {entry for entry in entries if entry not in claimed}
    sanitized = _sanitize(name)

    candidates = [canonical]

    if year is None:
        # Before the directory layout changed, the year was interpolated with an
        # unguarded f-string, so year-less media literally ended up on disk with the
        # string "(None)" in the directory name. Those directories are real and must
        # be adopted rather than orphaned.
        candidates.append(f"{sanitized} (None) [{provider}id-{external_id}]")

    # A metadata refresh overwrites `name`, so a directory created under an older
    # title no longer matches either name-based candidate. The embedded provider id
    # still identifies it unambiguously.
    token = re.compile(
        rf"\b{re.escape(provider)}(?:id)?[-_]?{re.escape(str(external_id))}\b",
        re.IGNORECASE,
    )
    id_matches = sorted(entry for entry in available if token.search(entry))
    if id_matches:
        # Lexicographically first, so a re-run of this migration picks the same one.
        candidates.append(id_matches[0])

    # The bare title carries no id, so it cannot distinguish two same-titled media;
    # it is only ever a last resort, after the id-bearing forms had their chance.
    candidates.append(sanitized)

    for candidate in candidates:
        if candidate in available:
            return candidate
    return canonical


def _load_parent_directories() -> Union[dict[str, tuple[Path, dict[str, Path]]], None]:
    """Map each table to its default parent directory and its configured libraries.

    Returns ``None`` if the configuration cannot be read at all, in which case every
    row is backfilled with its canonical name.
    """
    try:
        from media_manager.config import MediaManagerConfig

        misc = MediaManagerConfig().misc
    except Exception:
        return None
    return {
        "movie": (
            Path(misc.movie_directory),
            {library.name: Path(library.path) for library in misc.movie_libraries},
        ),
        "show": (
            Path(misc.tv_directory),
            {library.name: Path(library.path) for library in misc.tv_libraries},
        ),
    }


def _list_directories(
    parent: Path,
    cache: dict[Path, Union[list[str], None]],
) -> Union[list[str], None]:
    """List the sub-directories of ``parent`` once, or ``None`` if it cannot be read.

    Migrations legitimately run where the media volumes are not mounted (CI, restores,
    fresh installs). An unreadable parent must degrade to the canonical name instead
    of failing the migration or recording a wrong one.
    """
    if parent not in cache:
        try:
            cache[parent] = sorted(
                entry.name for entry in parent.iterdir() if entry.is_dir()
            )
        except Exception:
            cache[parent] = None
    return cache[parent]


def _backfill_directory_names(
    table_name: str,
    parents: Union[tuple[Path, dict[str, Path]], None],
) -> None:
    connection = op.get_bind()
    table = sa.table(
        table_name,
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("year", sa.Integer()),
        sa.column("metadata_provider", sa.String()),
        sa.column("external_id", sa.Integer()),
        sa.column("library", sa.String()),
        sa.column("directory_name", sa.String()),
    )

    rows = connection.execute(
        sa.select(
            table.c.id,
            table.c.name,
            table.c.year,
            table.c.metadata_provider,
            table.c.external_id,
            table.c.library,
        ).order_by(table.c.id)
    ).all()

    listings: dict[Path, Union[list[str], None]] = {}
    claimed: dict[Path, set[str]] = {}
    # A parent stand-in for rows whose parent directory is unknown; it never collides
    # with a real path and its listing is always unavailable.
    unknown_parent = Path("\x00unknown")

    for row_id, name, year, provider, external_id, library in rows:
        if parents is None:
            parent, entries = unknown_parent, None
        else:
            default_dir, libraries = parents
            parent = libraries.get(library, default_dir) if library else default_dir
            entries = _list_directories(parent, listings)

        parent_claims = claimed.setdefault(parent, set())
        directory_name = select_directory_name(
            name=name,
            year=year,
            provider=provider,
            external_id=external_id,
            entries=entries,
            claimed=parent_claims,
        )
        parent_claims.add(directory_name)

        connection.execute(
            table.update()
            .where(table.c.id == row_id)
            .values(directory_name=directory_name)
        )


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name, sa.Column("directory_name", sa.String(), nullable=True)
        )
    # Left NULL on purpose: a later scanner fills these in idempotently, so this
    # migration does no per-file filesystem work.
    for table_name in ("movie_file", "episode_file"):
        op.add_column(
            table_name, sa.Column("relative_path", sa.String(), nullable=True)
        )

    parents = _load_parent_directories()
    for table_name in ("movie", "show"):
        _backfill_directory_names(
            table_name, None if parents is None else parents[table_name]
        )
        op.alter_column(table_name, "directory_name", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie_file", "episode_file"):
        op.drop_column(table_name, "relative_path")
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "directory_name")
