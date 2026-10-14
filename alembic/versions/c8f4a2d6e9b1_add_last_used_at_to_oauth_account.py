"""Add last_used_at to oauth_account

Records when an OAuth account was last used to log in. Past logins weren't
recorded, so existing accounts are left NULL rather than guessed at.

Revision ID: c8f4a2d6e9b1
Revises: a3e9f1c27b84
Create Date: 2026-10-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8f4a2d6e9b1"
down_revision: Union[str, None] = "a3e9f1c27b84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "oauth_account",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("oauth_account", "last_used_at")
