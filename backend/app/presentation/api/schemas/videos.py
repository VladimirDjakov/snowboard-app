"""API request/response schemas for video endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateVideoRequest(BaseModel):
    """Request schema for creating a new video record."""

    filename: str = Field(..., description="Name of the video file")
    content_type: str = Field(..., description="MIME type (e.g., 'video/mp4')")
    size_bytes: int | None = Field(None, description="Optional file size in bytes", gt=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "ride.mp4",
                "content_type": "video/mp4",
                "size_bytes": 183742913,
            }
        }
    )


class UploadInfo(BaseModel):
    """Upload URL and metadata for presigned upload."""

    method: str = Field(..., description="HTTP method (typically 'PUT')")
    url: str = Field(..., description="Presigned URL for upload")
    headers: dict[str, str] = Field(..., description="Required headers (e.g., Content-Type)")
    storage_path: str = Field(..., description="Storage path to the artifact")
    expires_in_sec: int = Field(..., description="URL expiration time in seconds", gt=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "PUT",
                "url": "https://storage.local/raw/...presigned...",
                "headers": {"Content-Type": "video/mp4"},
                "storage_path": "raw/a2b6c4c8.../original.mp4",
                "expires_in_sec": 3600,
            }
        }
    )


class LimitsInfo(BaseModel):
    """Upload limits and constraints."""

    max_duration_sec: int = Field(..., description="Maximum video duration in seconds", gt=0)
    max_size_bytes: int = Field(..., description="Maximum file size in bytes", gt=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_duration_sec": 120,
                "max_size_bytes": 500000000,
            }
        }
    )


class CreateVideoResponse(BaseModel):
    """Response schema for video creation."""

    video_id: uuid.UUID = Field(..., description="Unique video identifier")
    share_token: str = Field(..., description="Token for accessing video without auth")
    upload: UploadInfo = Field(..., description="Upload URL and details")
    limits: LimitsInfo = Field(..., description="Upload constraints")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
                "share_token": "st_4f3f2b1a8b...",
                "upload": {
                    "method": "PUT",
                    "url": "https://storage.local/raw/...presigned...",
                    "headers": {"Content-Type": "video/mp4"},
                    "storage_path": "raw/a2b6c4c8.../original.mp4",
                    "expires_in_sec": 3600,
                },
                "limits": {
                    "max_duration_sec": 120,
                    "max_size_bytes": 500000000,
                },
            }
        }
    )


class ClientInfo(BaseModel):
    """Optional client metadata."""

    user_agent: str | None = Field(None, description="Browser user agent")
    timezone: str | None = Field(None, description="Client timezone")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_agent": "Mozilla/5.0",
                "timezone": "Europe/Amsterdam",
            }
        }
    )


class CompleteUploadRequest(BaseModel):
    """Request schema for completing video upload."""

    share_token: str = Field(..., description="Token to verify ownership")
    client: ClientInfo | None = Field(None, description="Optional client metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "share_token": "st_4f3f2b1a8b...",
                "client": {
                    "user_agent": "Mozilla/5.0",
                    "timezone": "Europe/Amsterdam",
                },
            }
        }
    )


class StageInfo(BaseModel):
    """Status information for a processing stage."""

    name: str = Field(..., description="Stage name (transcode, pose, features, feedback)")
    status: str = Field(..., description="Stage status (pending, queued, running, done, failed)")
    started_at: datetime | None = Field(None, description="When stage started")
    ended_at: datetime | None = Field(None, description="When stage completed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "transcode",
                "status": "queued",
                "started_at": None,
                "ended_at": None,
            }
        }
    )


class ProgressInfo(BaseModel):
    """Progress tracking information."""

    pct: float = Field(..., description="Overall progress percentage (0.0-1.0)", ge=0.0, le=1.0)
    stage: str | None = Field(None, description="Current active stage name")
    stage_pct: float | None = Field(
        None, description="Progress within current stage (0.0-1.0)", ge=0.0, le=1.0
    )
    eta_sec: int | None = Field(None, description="Estimated time remaining in seconds", ge=0)
    updated_at: datetime = Field(..., description="Last progress update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pct": 0.43,
                "stage": "pose",
                "stage_pct": 0.62,
                "eta_sec": None,
                "updated_at": "2026-01-07T10:58:12Z",
            }
        }
    )


class ArtifactInfo(BaseModel):
    """Information about a single artifact."""

    kind: str = Field(
        ..., description="Artifact type (original, normalized, keypoints, features, feedback)"
    )
    version: str = Field(..., description="Artifact version (e.g., 'v1')")
    url: str | None = Field(None, description="Presigned URL (null if not available)")
    expires_in_sec: int | None = Field(None, description="URL expiration time in seconds", gt=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kind": "normalized",
                "version": "v1",
                "url": "https://storage.local/...",
                "expires_in_sec": 900,
            }
        }
    )


class ArtifactsMap(BaseModel):
    """Map of artifact types to artifact info."""

    original: ArtifactInfo | None = Field(None, description="Original video artifact")
    normalized: ArtifactInfo | None = Field(None, description="Normalized video artifact")
    keypoints: ArtifactInfo | None = Field(None, description="Keypoints data artifact")
    features: ArtifactInfo | None = Field(None, description="Features data artifact")
    feedback: ArtifactInfo | None = Field(None, description="Feedback data artifact")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original": {
                    "kind": "original",
                    "version": "v1",
                    "url": "https://storage.local/...",
                    "expires_in_sec": 900,
                },
                "normalized": None,
                "keypoints": None,
                "features": None,
                "feedback": None,
            }
        }
    )


class CompleteUploadResponse(BaseModel):
    """Response schema for upload completion."""

    video_id: uuid.UUID = Field(..., description="Video identifier")
    status: str = Field(
        ..., description="Video status (created, uploaded, processing, done, failed, canceled)"
    )
    job_id: uuid.UUID | None = Field(None, description="Job identifier")
    pipeline_version: str | None = Field(None, description="Pipeline version")
    stages: list[StageInfo] = Field(..., description="List of processing stages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
                "status": "processing",
                "job_id": "c1c4b8f0-3aa2-4cb7-9fd8-2ef4c6e8f9a1",
                "pipeline_version": "mvp_v1",
                "stages": [
                    {"name": "transcode", "status": "queued"},
                    {"name": "pose", "status": "pending"},
                    {"name": "features", "status": "pending"},
                    {"name": "feedback", "status": "pending"},
                ],
            }
        }
    )


class VideoStatusResponse(BaseModel):
    """Response schema for video status and progress."""

    video_id: uuid.UUID = Field(..., description="Video identifier")
    status: str = Field(..., description="Video status")
    pipeline_version: str | None = Field(None, description="Pipeline version")
    progress: ProgressInfo = Field(..., description="Progress information")
    stages: list[StageInfo] = Field(..., description="Processing stages")
    artifacts: ArtifactsMap = Field(..., description="Available artifacts")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
                "status": "processing",
                "pipeline_version": "mvp_v1",
                "progress": {
                    "pct": 0.43,
                    "stage": "pose",
                    "stage_pct": 0.62,
                    "eta_sec": None,
                    "updated_at": "2026-01-07T10:58:12Z",
                },
                "stages": [
                    {"name": "transcode", "status": "done", "started_at": "...", "ended_at": "..."},
                    {"name": "pose", "status": "running", "started_at": "...", "ended_at": None},
                    {"name": "features", "status": "pending", "started_at": None, "ended_at": None},
                    {"name": "feedback", "status": "pending", "started_at": None, "ended_at": None},
                ],
                "artifacts": {
                    "original": {"url": "...", "expires_in_sec": 900},
                    "normalized": None,
                    "keypoints": None,
                    "features": None,
                    "feedback": None,
                },
                "errors": [],
            }
        }
    )


class ArtifactResponse(BaseModel):
    """Response schema for artifacts list."""

    video_id: uuid.UUID = Field(..., description="Video identifier")
    artifacts: list[ArtifactInfo] = Field(..., description="List of all artifacts")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "a2b6c4c8-2c28-4b3c-8e3e-1c0f1e0a3a2c",
                "artifacts": [
                    {"kind": "normalized", "version": "v1", "url": "...", "expires_in_sec": 900},
                    {"kind": "keypoints", "version": "v1", "url": "...", "expires_in_sec": 900},
                    {"kind": "features", "version": "v1", "url": "...", "expires_in_sec": 900},
                    {"kind": "feedback", "version": "v1", "url": "...", "expires_in_sec": 900},
                ],
            }
        }
    )
