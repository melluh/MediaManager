"""Add score_breakdown column to IndexerQueryResult table

Revision ID: c8d5e6f7a9b0
Revises: f1a2b3c4d5e6
Create Date: 2026-07-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d5e6f7a9b0"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "indexer_query_result",
        sa.Column(
            "score_breakdown",
            JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("indexer_query_result", "score_breakdown")
