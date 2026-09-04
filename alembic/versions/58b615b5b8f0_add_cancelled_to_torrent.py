"""Add cancelled column to torrent table

Revision ID: 58b615b5b8f0
Revises: a2c7d5e9f1b4
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58b615b5b8f0"
down_revision: Union[str, None] = "a2c7d5e9f1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "torrent",
        sa.Column(
            "cancelled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("torrent", "cancelled")
