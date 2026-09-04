"""Add added_by_user_id column to movie and show tables

Revision ID: a2c7d5e9f1b4
Revises: e1f4a8c2b6d9
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c7d5e9f1b4"
down_revision: Union[str, None] = "e1f4a8c2b6d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in ("movie", "show"):
        op.add_column(
            table_name,
            sa.Column("added_by_user_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            f"{table_name}_added_by_user_id_fkey",
            table_name,
            "user",
            ["added_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in ("movie", "show"):
        op.drop_constraint(
            f"{table_name}_added_by_user_id_fkey", table_name, type_="foreignkey"
        )
        op.drop_column(table_name, "added_by_user_id")
