"""Rename artifacts.object_key to storage_path

Revision ID: 003_add_storage_path
Revises: 002_add_version
Create Date: 2026-01-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_storage_path"
down_revision: str = "002_add_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("storage_path", sa.String(length=1024), nullable=True))
    op.execute(sa.text("UPDATE artifacts SET storage_path = object_key"))
    op.alter_column("artifacts", "storage_path", nullable=False)
    op.drop_column("artifacts", "object_key")


def downgrade() -> None:
    op.add_column("artifacts", sa.Column("object_key", sa.String(length=1024), nullable=True))
    op.execute(sa.text("UPDATE artifacts SET object_key = storage_path"))
    op.alter_column("artifacts", "object_key", nullable=False)
    op.drop_column("artifacts", "storage_path")
