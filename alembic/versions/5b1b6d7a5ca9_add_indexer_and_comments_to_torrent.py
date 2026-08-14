"""Add indexer and comments columns to torrent

Revision ID: 5b1b6d7a5ca9
Revises: 98b529ef6977
Create Date: 2026-08-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b1b6d7a5ca9"
down_revision: Union[str, None] = "98b529ef6977"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("torrent", sa.Column("indexer", sa.String(), nullable=True))
    op.add_column("torrent", sa.Column("comments", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("torrent", "comments")
    op.drop_column("torrent", "indexer")
