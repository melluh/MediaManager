"""rename username to display_name and drop unique constraint

Revision ID: f6fad872ddae
Revises: a1b2c3d4e5f6
Create Date: 2026-08-06 00:40:25.848275

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6fad872ddae"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("user_username_key"), "user", type_="unique")
    op.alter_column("user", "username", new_column_name="display_name")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("user", "display_name", new_column_name="username")
    op.create_unique_constraint(op.f("user_username_key"), "user", ["username"])
