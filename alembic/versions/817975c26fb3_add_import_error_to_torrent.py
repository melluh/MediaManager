"""Add import_error column to torrent

Revision ID: 817975c26fb3
Revises: 5b1b6d7a5ca9
Create Date: 2026-08-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "817975c26fb3"
down_revision: Union[str, None] = "5b1b6d7a5ca9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("torrent", sa.Column("import_error", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("torrent", "import_error")
