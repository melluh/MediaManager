"""Add metadata_version column to movie and show tables

Revision ID: 98b529ef6977
Revises: d4e5f6a7b8c9
Create Date: 2026-08-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98b529ef6977"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Existing rows are backfilled at the pre-CURRENT_METADATA_VERSION baseline
# (see common/schemas.py) so the next metadata-update pass picks them all up,
# regardless of how recently metadata_updated_at was touched.
LEGACY_METADATA_VERSION = "1"


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name,
            sa.Column(
                "metadata_version",
                sa.Integer(),
                nullable=False,
                server_default=LEGACY_METADATA_VERSION,
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "metadata_version")
