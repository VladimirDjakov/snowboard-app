"""Presenter for video endpoints (builds API response models)."""

from __future__ import annotations

from uuid import UUID

from backend.app.application.use_cases.video import (
    CompleteUploadResult,
    CreateVideoResult,
    VideoArtifactResult,
    VideoStatusResult,
)
from backend.app.presentation.api.schemas.videos import (
    ArtifactInfo,
    ArtifactResponse,
    ArtifactsMap,
    CompleteUploadResponse,
    CreateVideoResponse,
    LimitsInfo,
    ProgressInfo,
    StageInfo,
    UploadInfo,
    VideoStatusResponse,
)


class VideosPresenter:
    """Build Pydantic response models for videos API."""

    def present_create_video(self, result: CreateVideoResult) -> CreateVideoResponse:
        upload = UploadInfo(
            method=result.upload.method,
            url=result.upload.url,
            headers=result.upload.headers,
            storage_path=result.upload.storage_path,
            expires_in_sec=result.upload.expires_in_sec,
        )
        return CreateVideoResponse(
            video_id=result.video_id,
            share_token=result.share_token,
            upload=upload,
            limits=LimitsInfo(
                max_duration_sec=result.max_duration_sec,
                max_size_bytes=result.max_size_bytes,
            ),
        )

    def present_complete_upload(self, result: CompleteUploadResult) -> CompleteUploadResponse:
        stages = [
            StageInfo(
                name=s.name,
                status=s.status,
                started_at=s.started_at,
                ended_at=s.ended_at,
            )
            for s in result.stages
        ]
        return CompleteUploadResponse(
            video_id=result.video_id,
            status=result.status,
            job_id=result.job_id,
            pipeline_version=result.pipeline_version,
            stages=stages,
        )

    def present_video_status(self, result: VideoStatusResult) -> VideoStatusResponse:
        stages = [
            StageInfo(
                name=s.name,
                status=s.status,
                started_at=s.started_at,
                ended_at=s.ended_at,
            )
            for s in result.stages
        ]

        artifacts_map = {
            a.kind: ArtifactInfo(
                kind=a.kind, version=a.version, url=a.url, expires_in_sec=a.expires_in_sec
            )
            for a in result.artifacts
        }
        artifacts = ArtifactsMap(
            original=artifacts_map.get("original"),
            normalized=artifacts_map.get("normalized"),
            keypoints=artifacts_map.get("keypoints"),
            features=artifacts_map.get("features"),
            feedback=artifacts_map.get("feedback"),
        )

        progress = ProgressInfo(
            pct=result.progress_pct,
            stage=result.current_stage,
            stage_pct=None,
            eta_sec=None,
            updated_at=result.updated_at,
        )

        return VideoStatusResponse(
            video_id=result.video_id,
            status=result.status,
            pipeline_version=result.pipeline_version,
            progress=progress,
            stages=stages,
            artifacts=artifacts,
            errors=result.errors,
        )

    def present_artifacts_for_video(
        self,
        video_id: UUID,
        artifacts: list[VideoArtifactResult],
    ) -> ArtifactResponse:
        artifacts_response = [
            ArtifactInfo(kind=a.kind, version=a.version, url=a.url, expires_in_sec=a.expires_in_sec)
            for a in artifacts
        ]
        return ArtifactResponse(video_id=video_id, artifacts=artifacts_response)
