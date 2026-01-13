"""Add version column to videos table for optimistic locking

Revision ID: 002_add_version
Revises: 001_initial
Create Date: 2025-01-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_version"
down_revision: str = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add version column to videos table
    op.add_column("videos", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    # Remove version column from videos table
    op.drop_column("videos", "version")
