"""Add metadata_updated_at column to movie and show tables

Revision ID: d4e2b7c9a1f3
Revises: c3d9a1f6b2e4
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e2b7c9a1f3"
down_revision: Union[str, None] = "c3d9a1f6b2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name,
            sa.Column("metadata_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "metadata_updated_at")
