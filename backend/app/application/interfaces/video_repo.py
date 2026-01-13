"""Interface for video metadata repository (not analysis job)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from backend.app.domain.value_objects import VideoStatus


@dataclass(frozen=True, slots=True)
class VideoMeta:
    """Video metadata required by API/use-cases."""

    video_id: UUID
    status: VideoStatus
    share_token: str
    original_filename: str | None = None
    original_size_bytes: int | None = None


class VideoRepo(Protocol):
    """Interface for storing and retrieving video metadata."""

    def get(self, video_id: UUID) -> VideoMeta | None:
        """Return video metadata if present."""

    def create(
        self,
        *,
        video_id: UUID,
        share_token: str,
        status: VideoStatus,
        original_filename: str | None,
        original_size_bytes: int | None,
    ) -> VideoMeta:
        """Create and return a new video record."""

    def update_status(self, video_id: UUID, status: VideoStatus) -> None:
        """Update status for an existing video record."""
