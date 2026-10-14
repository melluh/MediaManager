"""Make notifications per-user and let them link to a movie or show

Notifications were global: every user saw, read and deleted the same list.
Each one now belongs to a single user. Existing notifications record nobody
they were meant for, so there's nothing exact to assign them to - they're
deleted rather than guessed at.

Notifications can also reference the movie or show they're about, so the UI
can show its poster and link to it.

Revision ID: a3e9f1c27b84
Revises: e3b8f2a6c1d4
Create Date: 2026-10-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3e9f1c27b84"
down_revision: Union[str, None] = "e3b8f2a6c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DELETE FROM notification")

    op.add_column("notification", sa.Column("user_id", sa.UUID(), nullable=False))
    op.create_foreign_key(
        "notification_user_id_fkey",
        "notification",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_notification_user_id"), "notification", ["user_id"]
    )

    op.add_column("notification", sa.Column("movie_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "notification_movie_id_fkey",
        "notification",
        "movie",
        ["movie_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("notification", sa.Column("show_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "notification_show_id_fkey",
        "notification",
        "show",
        ["show_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "notification_show_id_fkey", "notification", type_="foreignkey"
    )
    op.drop_column("notification", "show_id")
    op.drop_constraint(
        "notification_movie_id_fkey", "notification", type_="foreignkey"
    )
    op.drop_column("notification", "movie_id")
    op.drop_index(op.f("ix_notification_user_id"), table_name="notification")
    op.drop_constraint(
        "notification_user_id_fkey", "notification", type_="foreignkey"
    )
    op.drop_column("notification", "user_id")
