"""Add import_error_kind column to torrent

Revision ID: c4a6e9f1b3d7
Revises: 817975c26fb3
Create Date: 2026-08-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a6e9f1b3d7"
down_revision: Union[str, None] = "817975c26fb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "torrent", sa.Column("import_error_kind", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("torrent", "import_error_kind")
