"""Unit tests for video use cases."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from backend.app.application.interfaces.storage import PresignedUploadUrl
from backend.app.application.interfaces.video_repo import VideoMeta, VideoStatus
from backend.app.application.use_cases.video import (
    CompleteUpload,
    CreateVideo,
    GetVideoArtifacts,
    GetVideoStatus,
)
from backend.app.domain.analysis_job import AnalysisJob, AnalysisJobStatus, Stage, StageStatus
from backend.app.domain.value_objects import Artifact, ArtifactKind


class TestCreateVideo:
    """Tests for CreateVideo use case."""

    def test_execute_creates_video_with_upload_url(self) -> None:
        """Test that video is created with presigned upload URL."""
        mock_video_repo = MagicMock()
        mock_storage = MagicMock()
        mock_uow = MagicMock()

        upload_url = PresignedUploadUrl(
            method="PUT",
            url="https://storage.example.com/raw/test-id/original.mp4",
            headers={"Content-Type": "video/mp4"},
            storage_path="raw/test-id/original.mp4",
            expires_in_sec=3600,
        )
        mock_storage.generate_upload_url.return_value = upload_url

        # Use side_effect to return VideoMeta with the same video_id that was passed to create()
        def create_side_effect(**kwargs):
            return VideoMeta(
                video_id=kwargs["video_id"],
                status=kwargs["status"],
                share_token=kwargs["share_token"],
                original_filename=kwargs["original_filename"],
                original_size_bytes=kwargs["original_size_bytes"],
            )

        mock_video_repo.create.side_effect = create_side_effect

        use_case = CreateVideo(
            mock_video_repo,
            mock_storage,
            mock_uow,
            upload_url_ttl_sec=3600,
            max_duration_sec=120,
            max_size_bytes=500_000_000,
        )

        result = use_case.execute(
            filename="test.mp4",
            content_type="video/mp4",
            size_bytes=1024,
        )

        assert result.upload == upload_url
        assert result.max_duration_sec == 120
        assert result.max_size_bytes == 500_000_000

        mock_video_repo.create.assert_called_once()
        call_kwargs = mock_video_repo.create.call_args[1]
        assert call_kwargs["status"] == VideoStatus.CREATED
        assert call_kwargs["original_filename"] == "test.mp4"
        assert call_kwargs["original_size_bytes"] == 1024
        assert call_kwargs["video_id"] == result.video_id
        assert call_kwargs["share_token"] == result.share_token
        mock_storage.generate_upload_url.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_execute_creates_video_without_size(self) -> None:
        """Test that video can be created without size_bytes."""
        mock_video_repo = MagicMock()
        mock_storage = MagicMock()
        mock_uow = MagicMock()

        upload_url = PresignedUploadUrl(
            method="PUT",
            url="https://storage.example.com/raw/test-id/original.mp4",
            headers={"Content-Type": "video/mp4"},
            storage_path="raw/test-id/original.mp4",
            expires_in_sec=3600,
        )
        mock_storage.generate_upload_url.return_value = upload_url

        # Use side_effect to return VideoMeta with the same video_id that was passed to create()
        def create_side_effect(**kwargs):
            return VideoMeta(
                video_id=kwargs["video_id"],
                status=kwargs["status"],
                share_token=kwargs["share_token"],
                original_filename=kwargs["original_filename"],
                original_size_bytes=kwargs["original_size_bytes"],
            )

        mock_video_repo.create.side_effect = create_side_effect

        use_case = CreateVideo(mock_video_repo, mock_storage, mock_uow)
        result = use_case.execute(filename="test.mp4", content_type="video/mp4", size_bytes=None)

        assert isinstance(result.video_id, UUID)
        call_kwargs = mock_video_repo.create.call_args[1]
        assert call_kwargs["original_size_bytes"] is None
        assert call_kwargs["video_id"] == result.video_id

    def test_execute_uses_custom_ttl(self) -> None:
        """Test that custom TTL is used for upload URL."""
        mock_video_repo = MagicMock()
        mock_storage = MagicMock()
        mock_uow = MagicMock()

        upload_url = PresignedUploadUrl(
            method="PUT",
            url="https://storage.example.com/raw/test-id/original.mp4",
            headers={"Content-Type": "video/mp4"},
            storage_path="raw/test-id/original.mp4",
            expires_in_sec=7200,
        )
        mock_storage.generate_upload_url.return_value = upload_url

        video_meta = VideoMeta(
            video_id=uuid4(),
            status=VideoStatus.CREATED,
            share_token="st_test_token",
        )
        mock_video_repo.create.return_value = video_meta

        use_case = CreateVideo(mock_video_repo, mock_storage, mock_uow, upload_url_ttl_sec=7200)
        use_case.execute(filename="test.mp4", content_type="video/mp4", size_bytes=None)

        mock_storage.generate_upload_url.assert_called_once()
        call_kwargs = mock_storage.generate_upload_url.call_args[1]
        assert call_kwargs["expires_in"] == 7200


class TestCompleteUpload:
    """Tests for CompleteUpload use case."""

    def test_execute_completes_upload_and_starts_analysis(self) -> None:
        """Test that upload completion starts analysis pipeline."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_start_analysis = MagicMock()
        mock_get_status = MagicMock()
        mock_uow = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        job = AnalysisJob(video_id=video_id, status=AnalysisJobStatus.RUNNING)
        job.stages[Stage.NORMALIZE] = StageStatus.QUEUED
        job.stages[Stage.POSE] = StageStatus.PENDING
        job.stages[Stage.FEATURES] = StageStatus.PENDING
        job.stages[Stage.FEEDBACK] = StageStatus.PENDING
        mock_get_status.execute.return_value = job

        use_case = CompleteUpload(
            mock_video_repo,
            mock_start_analysis,
            mock_get_status,
            mock_uow,
            pipeline_version="mvp_v1",
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result.video_id == video_id
        assert result.status == AnalysisJobStatus.RUNNING.value
        assert result.job_id == video_id
        assert result.pipeline_version == "mvp_v1"
        assert len(result.stages) == 4

        mock_video_repo.get.assert_called_once_with(video_id)
        mock_video_repo.update_status.assert_called_once_with(video_id, VideoStatus.UPLOADED)
        mock_start_analysis.execute.assert_called_once_with(video_id)
        mock_get_status.execute.assert_called_once_with(video_id)
        mock_uow.commit.assert_called_once()

    def test_execute_raises_error_if_video_not_found(self) -> None:
        """Test that error is raised if video doesn't exist."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_start_analysis = MagicMock()
        mock_get_status = MagicMock()
        mock_uow = MagicMock()

        mock_video_repo.get.return_value = None

        use_case = CompleteUpload(mock_video_repo, mock_start_analysis, mock_get_status, mock_uow)

        with pytest.raises(ValueError, match="not found"):
            use_case.execute(video_id=video_id, share_token="st_test_token")

        mock_start_analysis.execute.assert_not_called()

    def test_execute_raises_error_if_invalid_token(self) -> None:
        """Test that error is raised if share token is invalid."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_start_analysis = MagicMock()
        mock_get_status = MagicMock()
        mock_uow = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token="st_correct_token",
        )
        mock_video_repo.get.return_value = video_meta

        use_case = CompleteUpload(mock_video_repo, mock_start_analysis, mock_get_status, mock_uow)

        with pytest.raises(PermissionError, match="Invalid share token"):
            use_case.execute(video_id=video_id, share_token="st_wrong_token")

        mock_start_analysis.execute.assert_not_called()

    def test_execute_raises_error_if_job_status_not_retrieved(self) -> None:
        """Test that error is raised if job status cannot be retrieved."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_start_analysis = MagicMock()
        mock_get_status = MagicMock()
        mock_uow = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta
        mock_get_status.execute.return_value = None

        use_case = CompleteUpload(mock_video_repo, mock_start_analysis, mock_get_status, mock_uow)

        with pytest.raises(RuntimeError, match="Failed to retrieve job status"):
            use_case.execute(video_id=video_id, share_token=share_token)


class TestGetVideoStatus:
    """Tests for GetVideoStatus use case."""

    def test_execute_returns_status_with_job(self) -> None:
        """Test that status is returned when job exists."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        job = AnalysisJob(video_id=video_id, status=AnalysisJobStatus.RUNNING)
        job.stages[Stage.NORMALIZE] = StageStatus.DONE
        job.stages[Stage.POSE] = StageStatus.RUNNING
        job.stages[Stage.FEATURES] = StageStatus.PENDING
        job.stages[Stage.FEEDBACK] = StageStatus.PENDING
        mock_get_status.execute.return_value = job

        artifacts = [
            Artifact(
                kind=ArtifactKind.NORMALIZED,
                version="v1",
                storage_path=f"proc/{video_id}/normalized.mp4",
            )
        ]
        mock_list_artifacts.execute.return_value = artifacts
        mock_storage.generate_download_url.return_value = "https://storage.example.com/download"

        use_case = GetVideoStatus(
            mock_video_repo,
            mock_get_status,
            mock_list_artifacts,
            mock_storage,
            download_url_ttl_sec=900,
            pipeline_version="mvp_v1",
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result.video_id == video_id
        assert result.status == AnalysisJobStatus.RUNNING.value
        assert result.pipeline_version == "mvp_v1"
        assert result.progress_pct == 0.25  # 1 out of 4 stages done
        assert result.current_stage == Stage.POSE.value
        assert len(result.stages) == 4
        assert len(result.artifacts) == 1
        assert result.artifacts[0].kind == ArtifactKind.NORMALIZED.value
        assert result.errors == []

        mock_get_status.execute.assert_called_once_with(video_id)
        mock_list_artifacts.execute.assert_called_once_with(video_id)
        mock_storage.generate_download_url.assert_called_once()

    def test_execute_returns_status_without_job(self) -> None:
        """Test that status is returned when job doesn't exist yet."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta
        mock_get_status.execute.return_value = None
        mock_list_artifacts.execute.return_value = None

        use_case = GetVideoStatus(
            mock_video_repo,
            mock_get_status,
            mock_list_artifacts,
            mock_storage,
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result.video_id == video_id
        assert result.status == VideoStatus.CREATED.value
        assert result.progress_pct == 0.0
        assert result.current_stage == Stage.NORMALIZE.value
        assert len(result.stages) == 4
        assert all(s.status == StageStatus.PENDING.value for s in result.stages)
        assert len(result.artifacts) == 0
        assert result.errors == []

    def test_execute_includes_errors_if_job_failed(self) -> None:
        """Test that errors are included if job has failed."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        job = AnalysisJob(video_id=video_id, status=AnalysisJobStatus.FAILED)
        job.error_message = "Processing failed"
        job.stages[Stage.NORMALIZE] = StageStatus.FAILED
        mock_get_status.execute.return_value = job
        mock_list_artifacts.execute.return_value = []

        use_case = GetVideoStatus(
            mock_video_repo,
            mock_get_status,
            mock_list_artifacts,
            mock_storage,
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result.status == AnalysisJobStatus.FAILED.value
        assert result.errors == ["Processing failed"]

    def test_execute_raises_error_if_video_not_found(self) -> None:
        """Test that error is raised if video doesn't exist."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        mock_video_repo.get.return_value = None

        use_case = GetVideoStatus(
            mock_video_repo, mock_get_status, mock_list_artifacts, mock_storage
        )

        with pytest.raises(ValueError, match="not found"):
            use_case.execute(video_id=video_id, share_token="st_test_token")

    def test_execute_raises_error_if_invalid_token(self) -> None:
        """Test that error is raised if share token is invalid."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token="st_correct_token",
        )
        mock_video_repo.get.return_value = video_meta

        use_case = GetVideoStatus(
            mock_video_repo, mock_get_status, mock_list_artifacts, mock_storage
        )

        with pytest.raises(PermissionError, match="Invalid share token"):
            use_case.execute(video_id=video_id, share_token="st_wrong_token")

    def test_execute_calculates_progress_correctly(self) -> None:
        """Test that progress percentage is calculated correctly."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_get_status = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        job = AnalysisJob(video_id=video_id, status=AnalysisJobStatus.RUNNING)
        job.stages[Stage.NORMALIZE] = StageStatus.DONE
        job.stages[Stage.POSE] = StageStatus.DONE
        job.stages[Stage.FEATURES] = StageStatus.DONE
        job.stages[Stage.FEEDBACK] = StageStatus.RUNNING
        mock_get_status.execute.return_value = job
        mock_list_artifacts.execute.return_value = []

        use_case = GetVideoStatus(
            mock_video_repo,
            mock_get_status,
            mock_list_artifacts,
            mock_storage,
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result.progress_pct == 0.75  # 3 out of 4 stages done


class TestGetVideoArtifacts:
    """Tests for GetVideoArtifacts use case."""

    def test_execute_returns_artifacts_with_urls(self) -> None:
        """Test that artifacts are returned with presigned download URLs."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        artifacts = [
            Artifact(
                kind=ArtifactKind.NORMALIZED,
                version="v1",
                storage_path=f"proc/{video_id}/normalized.mp4",
            ),
            Artifact(
                kind=ArtifactKind.KEYPOINTS,
                version="v1",
                storage_path=f"proc/{video_id}/keypoints_v1.jsonl",
            ),
        ]
        mock_list_artifacts.execute.return_value = artifacts
        mock_storage.generate_download_url.side_effect = [
            "https://storage.example.com/normalized",
            "https://storage.example.com/keypoints",
        ]

        use_case = GetVideoArtifacts(
            mock_video_repo,
            mock_list_artifacts,
            mock_storage,
            download_url_ttl_sec=900,
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert len(result) == 2
        assert result[0].kind == ArtifactKind.NORMALIZED.value
        assert result[0].version == "v1"
        assert result[0].url == "https://storage.example.com/normalized"
        assert result[0].expires_in_sec == 900
        assert result[1].kind == ArtifactKind.KEYPOINTS.value

        mock_list_artifacts.execute.assert_called_once_with(video_id)
        assert mock_storage.generate_download_url.call_count == 2

    def test_execute_returns_empty_list_if_no_artifacts(self) -> None:
        """Test that empty list is returned when no artifacts exist."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta
        mock_list_artifacts.execute.return_value = []

        use_case = GetVideoArtifacts(mock_video_repo, mock_list_artifacts, mock_storage)

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result == []
        mock_storage.generate_download_url.assert_not_called()

    def test_execute_handles_none_artifacts(self) -> None:
        """Test that None artifacts list is handled correctly."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta
        mock_list_artifacts.execute.return_value = None

        use_case = GetVideoArtifacts(mock_video_repo, mock_list_artifacts, mock_storage)

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result == []

    def test_execute_raises_error_if_video_not_found(self) -> None:
        """Test that error is raised if video doesn't exist."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        mock_video_repo.get.return_value = None

        use_case = GetVideoArtifacts(mock_video_repo, mock_list_artifacts, mock_storage)

        with pytest.raises(ValueError, match="not found"):
            use_case.execute(video_id=video_id, share_token="st_test_token")

    def test_execute_raises_error_if_invalid_token(self) -> None:
        """Test that error is raised if share token is invalid."""
        video_id = uuid4()
        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.CREATED,
            share_token="st_correct_token",
        )
        mock_video_repo.get.return_value = video_meta

        use_case = GetVideoArtifacts(mock_video_repo, mock_list_artifacts, mock_storage)

        with pytest.raises(PermissionError, match="Invalid share token"):
            use_case.execute(video_id=video_id, share_token="st_wrong_token")

    def test_execute_uses_custom_ttl(self) -> None:
        """Test that custom TTL is used for download URLs."""
        video_id = uuid4()
        share_token = "st_test_token"

        mock_video_repo = MagicMock()
        mock_list_artifacts = MagicMock()
        mock_storage = MagicMock()

        video_meta = VideoMeta(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            share_token=share_token,
        )
        mock_video_repo.get.return_value = video_meta

        artifacts = [
            Artifact(
                kind=ArtifactKind.NORMALIZED,
                version="v1",
                storage_path=f"proc/{video_id}/normalized.mp4",
            )
        ]
        mock_list_artifacts.execute.return_value = artifacts
        mock_storage.generate_download_url.return_value = "https://storage.example.com/download"

        use_case = GetVideoArtifacts(
            mock_video_repo,
            mock_list_artifacts,
            mock_storage,
            download_url_ttl_sec=1800,
        )

        result = use_case.execute(video_id=video_id, share_token=share_token)

        assert result[0].expires_in_sec == 1800
        mock_storage.generate_download_url.assert_called_once()
        call_kwargs = mock_storage.generate_download_url.call_args[1]
        assert call_kwargs["expires_in"] == 1800
