"""Rename job stage from transcode to normalize

Revision ID: 004_rename_transcode_norm
Revises: 003_add_storage_path
Create Date: 2026-01-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_rename_transcode_norm"
down_revision: str | None = "003_add_storage_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE job_stages SET name = 'normalize' WHERE name = 'transcode'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE job_stages SET name = 'transcode' WHERE name = 'normalize'"))
