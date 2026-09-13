"""Add air_date column to season table

Revision ID: 863237bcbf1d
Revises: 58b615b5b8f0
Create Date: 2026-09-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "863237bcbf1d"
down_revision: Union[str, None] = "58b615b5b8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "season",
        sa.Column("air_date", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("season", "air_date")
