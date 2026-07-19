"""Add tagline, genres, runtime and release_date columns to movie and show tables

Revision ID: c3d9a1f6b2e4
Revises: b2b452fcef23
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d9a1f6b2e4"
down_revision: Union[str, None] = "b2b452fcef23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(table_name, sa.Column("tagline", sa.String(), nullable=True))
        op.add_column(
            table_name,
            sa.Column("genres", postgresql.ARRAY(sa.String()), nullable=True),
        )
        op.add_column(table_name, sa.Column("runtime", sa.Integer(), nullable=True))
        op.add_column(
            table_name, sa.Column("release_date", sa.String(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "release_date")
        op.drop_column(table_name, "runtime")
        op.drop_column(table_name, "genres")
        op.drop_column(table_name, "tagline")
