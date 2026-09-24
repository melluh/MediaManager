"""Create media_image table

Revision ID: b4c1e7d92a3f
Revises: 863237bcbf1d
Create Date: 2026-09-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c1e7d92a3f"
down_revision: Union[str, None] = "863237bcbf1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media_image",
        sa.Column("media_id", sa.UUID(), nullable=False),
        sa.Column("image_type", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("media_id", "image_type"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("media_image")
