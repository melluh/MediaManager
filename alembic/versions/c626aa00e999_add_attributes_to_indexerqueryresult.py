"""add attributes column to indexerqueryresult

Revision ID: c626aa00e999
Revises: c8d5e6f7a9b0
Create Date: 2026-07-30 19:20:26.188958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c626aa00e999'
down_revision: Union[str, None] = 'c8d5e6f7a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "indexer_query_result",
        sa.Column("attributes", JSONB(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("indexer_query_result", "attributes")
