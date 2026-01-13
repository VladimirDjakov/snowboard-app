"""Use case: Get video status, stages, progress, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from backend.app.application.dtos import StageView
from backend.app.application.ports.storage import Storage
from backend.app.application.ports.video_repo import VideoRepo
from backend.app.application.use_cases.get_status import GetAnalysisStatus
from backend.app.application.use_cases.list_artifacts import ListArtifacts
from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import ArtifactRef


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

        artifacts_list: list[ArtifactRef] = self._list_artifacts.execute(video_id) or []
        artifacts_with_urls: list[ArtifactWithUrl] = []
        for artifact in artifacts_list:
            url = self._storage.generate_download_url(
                object_key=artifact.object_key,
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
