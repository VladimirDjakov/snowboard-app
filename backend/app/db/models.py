"""Database models for video processing pipeline."""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class VideoStatus(str, Enum):
    """Video processing status."""

    CREATED = "created"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class JobStageName(str, Enum):
    """Job stage names."""

    TRANSCODE = "transcode"
    POSE = "pose"
    FEATURES = "features"
    FEEDBACK = "feedback"


class JobStageStatus(str, Enum):
    """Job stage processing status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ArtifactKind(str, Enum):
    """Artifact kinds."""

    ORIGINAL = "original"
    NORMALIZED = "normalized"
    KEYPOINTS = "keypoints"
    FEATURES = "features"
    FEEDBACK = "feedback"


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
    name: Mapped[JobStageName] = mapped_column(
        SQLEnum(JobStageName, native_enum=False),
        nullable=False,
    )
    status: Mapped[JobStageStatus] = mapped_column(
        SQLEnum(JobStageStatus, native_enum=False),
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
