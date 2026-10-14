"""Create media_server_account table

Links MediaManager users to their account on the configured media server
(e.g. Jellyfin).

Revision ID: e3b8f2a6c1d4
Revises: d7a2c9e41b6f
Create Date: 2026-10-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3b8f2a6c1d4"
down_revision: Union[str, None] = "d7a2c9e41b6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media_server_account",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=320), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider"),
        sa.UniqueConstraint("provider", "external_user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("media_server_account")
