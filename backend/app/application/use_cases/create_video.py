"""Use case: Create a new video + presigned upload URL."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from backend.app.application.ports.storage import PresignedUploadUrl, Storage
from backend.app.application.ports.uow import UnitOfWork
from backend.app.application.ports.video_repo import VideoLifecycleStatus, VideoRepo


def _generate_share_token() -> str:
    return f"st_{secrets.token_urlsafe(32)}"


@dataclass(frozen=True, slots=True)
class CreateVideoResult:
    video_id: uuid.UUID
    share_token: str
    upload: PresignedUploadUrl
    max_duration_sec: int
    max_size_bytes: int


class CreateVideo:
    """Create a new video record and generate presigned upload URL."""

    def __init__(
        self,
        video_repo: VideoRepo,
        storage: Storage,
        uow: UnitOfWork,
        *,
        upload_url_ttl_sec: int = 3600,
        max_duration_sec: int = 120,
        max_size_bytes: int = 500_000_000,
    ) -> None:
        self._video_repo = video_repo
        self._storage = storage
        self._uow = uow
        self._upload_url_ttl_sec = upload_url_ttl_sec
        self._max_duration_sec = max_duration_sec
        self._max_size_bytes = max_size_bytes

    def execute(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int | None,
    ) -> CreateVideoResult:
        video_id = uuid.uuid4()
        share_token = _generate_share_token()

        object_key = f"raw/{video_id}/original.mp4"
        upload = self._storage.generate_upload_url(
            object_key=object_key,
            content_type=content_type,
            expires_in=self._upload_url_ttl_sec,
        )

        self._video_repo.create(
            video_id=video_id,
            share_token=share_token,
            status=VideoLifecycleStatus.CREATED,
            original_filename=filename,
            original_size_bytes=size_bytes,
        )
        self._uow.commit()

        return CreateVideoResult(
            video_id=video_id,
            share_token=share_token,
            upload=upload,
            max_duration_sec=self._max_duration_sec,
            max_size_bytes=self._max_size_bytes,
        )
