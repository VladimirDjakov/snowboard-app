"""PostgreSQL ORM models for video processing pipeline.

These models are part of the PostgreSQL infrastructure implementation.
They are used by adapters and should not be imported by domain/application layers.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import ArtifactKind
from backend.app.infrastructure.postgres.session import Base


class VideoStatus(str, Enum):
    """Video processing status (lifecycle status, not domain logic)."""

    CREATED = "created"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class Video(Base):
    """Video model - contains only basic information about the video file."""

    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    status: Mapped[VideoStatus] = mapped_column(
        SQLEnum(VideoStatus, native_enum=False),
        nullable=False,
        index=True,
    )
    share_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    stages: Mapped[list["JobStage"]] = relationship(
        "JobStage",
        back_populates="video",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="video",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, status={self.status.value})>"


class JobStage(Base):
    """Job stage model - tracks processing stages and optionally stores versioning information."""

    __tablename__ = "job_stages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[Stage] = mapped_column(
        SQLEnum(Stage, native_enum=False),
        nullable=False,
    )
    status: Mapped[StageStatus] = mapped_column(
        SQLEnum(StageStatus, native_enum=False),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="stages")

    # Constraints
    __table_args__ = (
        UniqueConstraint("video_id", "name", name="uq_job_stage_video_name"),
        Index("idx_job_stages_video_id", "video_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<JobStage(id={self.id}, video_id={self.video_id}, "
            f"name={self.name.value}, status={self.status.value})>"
        )


class Artifact(Base):
    """Artifact model - stores references to files produced during processing."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[ArtifactKind] = mapped_column(
        SQLEnum(ArtifactKind, native_enum=False),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="artifacts")

    # Constraints
    __table_args__ = (
        UniqueConstraint("video_id", "kind", "version", name="uq_artifact_video_kind_version"),
        Index("idx_artifacts_video_id", "video_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Artifact(id={self.id}, video_id={self.video_id}, "
            f"kind={self.kind.value}, version={self.version})>"
        )
