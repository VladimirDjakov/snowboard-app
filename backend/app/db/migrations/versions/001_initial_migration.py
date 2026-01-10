"""Initial migration: create videos, job_stages, and artifacts tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-20 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create videos table
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("share_token", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=True),
        sa.Column("original_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_videos_id", "videos", ["id"], unique=False)
    op.create_index("idx_videos_share_token", "videos", ["share_token"], unique=True)
    op.create_index("idx_videos_status", "videos", ["status"], unique=False)

    # Create job_stages table
    op.create_table(
        "job_stages",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pipeline_version", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "name", name="uq_job_stage_video_name"),
    )
    op.create_index("idx_job_stages_video_id", "job_stages", ["video_id"], unique=False)
    op.create_index("idx_job_stages_status", "job_stages", ["status"], unique=False)

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "kind", "version", name="uq_artifact_video_kind_version"),
    )
    op.create_index("idx_artifacts_video_id", "artifacts", ["video_id"], unique=False)


def downgrade() -> None:
    # Drop artifacts table
    op.drop_index("idx_artifacts_video_id", table_name="artifacts")
    op.drop_table("artifacts")

    # Drop job_stages table
    op.drop_index("idx_job_stages_status", table_name="job_stages")
    op.drop_index("idx_job_stages_video_id", table_name="job_stages")
    op.drop_table("job_stages")

    # Drop videos table
    op.drop_index("idx_videos_status", table_name="videos")
    op.drop_index("idx_videos_share_token", table_name="videos")
    op.drop_index("idx_videos_id", table_name="videos")
    op.drop_table("videos")
