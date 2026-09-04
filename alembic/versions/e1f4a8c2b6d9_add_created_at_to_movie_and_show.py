"""Add created_at column to movie and show tables

Revision ID: e1f4a8c2b6d9
Revises: b7e1c4d9a2f5
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f4a8c2b6d9"
down_revision: Union[str, None] = "b7e1c4d9a2f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_column(table_name, "created_at")
