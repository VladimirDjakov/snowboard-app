"""Use cases for video lifecycle management."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from backend.app.application.dtos import StageView
from backend.app.application.interfaces.storage import PresignedUploadUrl, Storage
from backend.app.application.interfaces.uow import UnitOfWork
from backend.app.application.interfaces.video_repo import VideoRepo, VideoStatus
from backend.app.application.use_cases.analysis import (
    GetAnalysisStatus,
    ListArtifacts,
    StartAnalysis,
)
from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import Artifact


def _generate_share_token() -> str:
    return f"st_{secrets.token_urlsafe(32)}"


@dataclass(frozen=True, slots=True)
class CreateVideoResult:
    video_id: uuid.UUID
    share_token: str
    upload: PresignedUploadUrl
    max_duration_sec: int
    max_size_bytes: int


@dataclass(frozen=True, slots=True)
class CompleteUploadResult:
    video_id: UUID
    status: str
    job_id: UUID
    pipeline_version: str | None
    stages: list[StageView]


@dataclass(frozen=True, slots=True)
class ArtifactWithUrl:
    kind: str
    version: str
    url: str
    expires_in_sec: int


@dataclass(frozen=True, slots=True)
class VideoStatusResult:
    video_id: UUID
    status: str
    pipeline_version: str | None
    progress_pct: float
    current_stage: str | None
    updated_at: datetime
    stages: list[StageView]
    artifacts: list[ArtifactWithUrl]
    errors: list[str]


@dataclass(frozen=True, slots=True)
class VideoArtifactResult:
    kind: str
    version: str
    url: str
    expires_in_sec: int


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

        storage_path = f"raw/{video_id}/original.mp4"
        upload = self._storage.generate_upload_url(
            storage_path=storage_path,
            content_type=content_type,
            expires_in=self._upload_url_ttl_sec,
        )

        self._video_repo.create(
            video_id=video_id,
            share_token=share_token,
            status=VideoStatus.CREATED,
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


class CompleteUpload:
    """Confirm upload completion and start analysis pipeline."""

    def __init__(
        self,
        video_repo: VideoRepo,
        start_analysis: StartAnalysis,
        get_status: GetAnalysisStatus,
        uow: UnitOfWork,
        *,
        pipeline_version: str = "mvp_v1",
    ) -> None:
        self._video_repo = video_repo
        self._start_analysis = start_analysis
        self._get_status = get_status
        self._uow = uow
        self._pipeline_version = pipeline_version

    def execute(self, *, video_id: UUID, share_token: str) -> CompleteUploadResult:
        video = self._video_repo.get(video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")
        if video.share_token != share_token:
            raise PermissionError("Invalid share token")

        # Mark as UPLOADED (best-effort; StartAnalysis will move it to PROCESSING)
        self._video_repo.update_status(video_id, VideoStatus.UPLOADED)

        self._start_analysis.execute(video_id)

        job = self._get_status.execute(video_id)
        if job is None:
            raise RuntimeError("Failed to retrieve job status")

        stages = [
            StageView(
                name=stage.value,
                status=job.stages.get(stage, StageStatus.PENDING).value,
                started_at=None,
                ended_at=None,
            )
            for stage in Stage
        ]

        # StartAnalysis commits, but keep request boundary consistent
        self._uow.commit()

        return CompleteUploadResult(
            video_id=video_id,
            status=job.status.value,
            job_id=video_id,
            pipeline_version=self._pipeline_version,
            stages=stages,
        )


class GetVideoStatus:
    """Aggregate status for the video pipeline."""

    def __init__(
        self,
        video_repo: VideoRepo,
        get_status: GetAnalysisStatus,
        list_artifacts: ListArtifacts,
        storage: Storage,
        *,
        download_url_ttl_sec: int = 900,
        pipeline_version: str = "mvp_v1",
    ) -> None:
        self._video_repo = video_repo
        self._get_status = get_status
        self._list_artifacts = list_artifacts
        self._storage = storage
        self._download_url_ttl_sec = download_url_ttl_sec
        self._pipeline_version = pipeline_version

    def execute(self, *, video_id: UUID, share_token: str) -> VideoStatusResult:
        video = self._video_repo.get(video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")
        if video.share_token != share_token:
            raise PermissionError("Invalid share token")

        job = self._get_status.execute(video_id)

        if job is None:
            status = video.status.value
            progress_pct = 0.0
            errors: list[str] = []
            stages = [
                StageView(name=stage.value, status=StageStatus.PENDING.value) for stage in Stage
            ]
        else:
            status = job.status.value
            done_stages = sum(1 for s in job.stages.values() if s == StageStatus.DONE)
            progress_pct = done_stages / len(Stage) if len(Stage) else 0.0
            errors = [job.error_message] if job.error_message else []
            stages = [
                StageView(
                    name=stage.value,
                    status=job.stages.get(stage, StageStatus.PENDING).value,
                    started_at=None,
                    ended_at=None,
                )
                for stage in Stage
            ]

        current_stage = None
        for st in stages:
            if st.status != StageStatus.DONE.value:
                current_stage = st.name
                break

        artifacts_list: list[Artifact] = self._list_artifacts.execute(video_id) or []
        artifacts_with_urls: list[ArtifactWithUrl] = []
        for artifact in artifacts_list:
            url = self._storage.generate_download_url(
                storage_path=artifact.storage_path,
                expires_in=self._download_url_ttl_sec,
            )
            artifacts_with_urls.append(
                ArtifactWithUrl(
                    kind=artifact.kind.value,
                    version=artifact.version,
                    url=url,
                    expires_in_sec=self._download_url_ttl_sec,
                )
            )

        return VideoStatusResult(
            video_id=video_id,
            status=status,
            pipeline_version=self._pipeline_version,
            progress_pct=progress_pct,
            current_stage=current_stage,
            updated_at=datetime.now(UTC),
            stages=stages,
            artifacts=artifacts_with_urls,
            errors=errors,
        )


class GetVideoArtifacts:
    """Return all artifacts for a video with presigned download URLs."""

    def __init__(
        self,
        video_repo: VideoRepo,
        list_artifacts: ListArtifacts,
        storage: Storage,
        *,
        download_url_ttl_sec: int = 900,
    ) -> None:
        self._video_repo = video_repo
        self._list_artifacts = list_artifacts
        self._storage = storage
        self._download_url_ttl_sec = download_url_ttl_sec

    def execute(self, *, video_id: UUID, share_token: str) -> list[VideoArtifactResult]:
        video = self._video_repo.get(video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")
        if video.share_token != share_token:
            raise PermissionError("Invalid share token")

        artifacts_list: list[Artifact] = self._list_artifacts.execute(video_id) or []
        results: list[VideoArtifactResult] = []
        for artifact in artifacts_list:
            url = self._storage.generate_download_url(
                storage_path=artifact.storage_path,
                expires_in=self._download_url_ttl_sec,
            )
            results.append(
                VideoArtifactResult(
                    kind=artifact.kind.value,
                    version=artifact.version,
                    url=url,
                    expires_in_sec=self._download_url_ttl_sec,
                )
            )
        return results
