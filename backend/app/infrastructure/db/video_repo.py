"""PostgreSQL adapter for VideoRepo."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.application.interfaces.video_repo import VideoMeta, VideoRepo
from backend.app.domain.value_objects import VideoStatus
from backend.app.infrastructure.db.orm_models import VideoDB


class PostgresVideoRepo(VideoRepo):
    """SQLAlchemy implementation of VideoRepo."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, video_id: UUID) -> VideoMeta | None:
        video = self._session.get(VideoDB, video_id)
        if video is None:
            return None
        return self._to_meta(video)

    def create(
        self,
        *,
        video_id: UUID,
        share_token: str,
        status: VideoStatus,
        original_filename: str | None,
        original_size_bytes: int | None,
    ) -> VideoMeta:
        video = VideoDB(
            id=video_id,
            status=status,
            share_token=share_token,
            original_filename=original_filename,
            original_size_bytes=original_size_bytes,
        )
        self._session.add(video)
        # Commit handled by UoW/session owner (API request boundary)
        self._session.flush()
        return self._to_meta(video)

    def update_status(self, video_id: UUID, status: VideoStatus) -> None:
        video = self._session.get(VideoDB, video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")
        video.status = status
        self._session.flush()

    @staticmethod
    def _to_meta(video: VideoDB) -> VideoMeta:
        return VideoMeta(
            video_id=video.id,
            status=VideoStatus(video.status.value),
            share_token=video.share_token,
            original_filename=video.original_filename,
            original_size_bytes=video.original_size_bytes,
        )
