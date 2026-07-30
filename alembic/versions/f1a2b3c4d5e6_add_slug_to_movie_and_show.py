"""Add slug column to movie and show tables

Revision ID: f1a2b3c4d5e6
Revises: 990f9fbb5b57
Create Date: 2026-07-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from slugify import slugify

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "990f9fbb5b57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slug_for(name: str, year: int | None, row_id, seen: set[str]) -> str:
    base = slugify(name) or "untitled"
    if year is not None:
        base = f"{base}-{year}"

    slug = base
    if slug in seen:
        slug = f"{base}-{row_id.hex[:8]}"
    seen.add(slug)
    return slug


def _backfill_slugs(table_name: str, *, include_year: bool) -> None:
    connection = op.get_bind()
    table = sa.table(
        table_name,
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("year", sa.Integer()),
        sa.column("slug", sa.String()),
    )

    rows = connection.execute(sa.select(table.c.id, table.c.name, table.c.year)).all()

    seen: set[str] = set()
    for row_id, name, year in rows:
        slug = _slug_for(name, year if include_year else None, row_id, seen)
        connection.execute(
            table.update().where(table.c.id == row_id).values(slug=slug)
        )


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(table_name, sa.Column("slug", sa.String(), nullable=True))

    _backfill_slugs("movie", include_year=True)
    _backfill_slugs("show", include_year=False)

    for table_name in ("movie", "show"):
        op.alter_column(table_name, "slug", nullable=False)
        op.create_unique_constraint(op.f(f"{table_name}_slug_key"), table_name, ["slug"])


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_constraint(op.f(f"{table_name}_slug_key"), table_name, type_="unique")
        op.drop_column(table_name, "slug")
