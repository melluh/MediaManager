"""Add initiated_by_user_id and initiated_at to torrent

Revision ID: a7c3f912e5b8
Revises: d4e2b7c9a1f3
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3f912e5b8"
down_revision: Union[str, None] = "d4e2b7c9a1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "torrent", sa.Column("initiated_by_user_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "torrent",
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "torrent_initiated_by_user_id_fkey",
        "torrent",
        "user",
        ["initiated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "torrent_initiated_by_user_id_fkey", "torrent", type_="foreignkey"
    )
    op.drop_column("torrent", "initiated_at")
    op.drop_column("torrent", "initiated_by_user_id")
