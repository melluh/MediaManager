"""add created_at column to indexerqueryresult and clear stale rows

Revision ID: a1b2c3d4e5f6
Revises: c626aa00e999
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c626aa00e999"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # indexer_query_result has been growing unbounded since results were
    # never expired. Rather than backfilling created_at for existing rows
    # (their real query time is unknown), drop everything and start fresh
    # with a 6-hour expiry enforced by a periodic cleanup task.
    op.execute("TRUNCATE TABLE indexer_query_result")
    op.add_column(
        "indexer_query_result",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("indexer_query_result", "created_at")
