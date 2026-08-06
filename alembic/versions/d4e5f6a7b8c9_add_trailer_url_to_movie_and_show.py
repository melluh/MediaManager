"""Add trailer_url column to movie and show tables

Revision ID: d4e5f6a7b8c9
Revises: f6fad872ddae
Create Date: 2026-08-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "f6fad872ddae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name, sa.Column("trailer_url", sa.String(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "trailer_url")
