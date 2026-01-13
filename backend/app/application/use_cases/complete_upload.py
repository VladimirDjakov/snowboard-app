"""Use case: Complete upload (verify token, mark uploaded, start pipeline)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.app.application.dtos import StageView
from backend.app.application.ports.uow import UnitOfWork
from backend.app.application.ports.video_repo import VideoLifecycleStatus, VideoRepo
from backend.app.application.use_cases.get_status import GetAnalysisStatus
from backend.app.application.use_cases.start_analysis import StartAnalysis
from backend.app.domain.analysis_job import Stage, StageStatus


@dataclass(frozen=True, slots=True)
class CompleteUploadResult:
    video_id: UUID
    status: str
    job_id: UUID
    pipeline_version: str | None
    stages: list[StageView]


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
        self._video_repo.update_status(video_id, VideoLifecycleStatus.UPLOADED)

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
