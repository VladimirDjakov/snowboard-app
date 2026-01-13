"""Unit tests for use cases."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.application.use_cases.fail_analysis import FailAnalysis
from backend.app.application.use_cases.finalize_analysis import FinalizeAnalysis
from backend.app.application.use_cases.get_status import GetAnalysisStatus
from backend.app.application.use_cases.handle_stage_completed import HandleStageCompleted
from backend.app.application.use_cases.start_analysis import StartAnalysis
from backend.app.domain.analysis_job import (
    AnalysisJob,
    AnalysisJobStatus,
    Stage,
    StageStatus,
)


class TestStartAnalysis:
    """Tests for StartAnalysis use case."""

    def test_execute_creates_job_if_not_exists(self) -> None:
        """Test that job is created if it doesn't exist."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_queue = MagicMock()
        mock_clock = MagicMock()

        # Job doesn't exist
        mock_job_repo.lock_job.return_value = None
        mock_job_repo.create_job.return_value = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.CREATED,
        )

        mock_uow = MagicMock()
        use_case = StartAnalysis(mock_job_repo, mock_queue, mock_clock, mock_uow)
        use_case.execute(video_id)
        mock_uow.commit.assert_called_once()

        mock_job_repo.create_job.assert_called_once_with(video_id)
        mock_queue.publish.assert_called_once()
        mock_job_repo.save_job.assert_called_once()

    def test_execute_raises_error_if_not_created_status(self) -> None:
        """Test that error is raised if job is not in CREATED status."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_queue = MagicMock()
        mock_clock = MagicMock()

        existing_job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        mock_job_repo.lock_job.return_value = existing_job

        mock_uow = MagicMock()
        use_case = StartAnalysis(mock_job_repo, mock_queue, mock_clock, mock_uow)

        with pytest.raises(ValueError, match="Cannot start analysis"):
            use_case.execute(video_id)


class TestHandleStageCompleted:
    """Tests for HandleStageCompleted use case."""

    def test_execute_idempotent_if_stage_already_done(self) -> None:
        """Test that completing an already DONE stage is idempotent."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_queue = MagicMock()
        mock_clock = MagicMock()
        mock_uow = MagicMock()

        # Job with stage already DONE
        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        job.stages[Stage.TRANSCODE] = StageStatus.DONE
        mock_job_repo.lock_job.return_value = job

        use_case = HandleStageCompleted(mock_job_repo, mock_queue, mock_clock, mock_uow)
        use_case.execute(video_id, Stage.TRANSCODE, [])

        # Should not call commit (early return)
        mock_uow.commit.assert_not_called()
        mock_queue.publish.assert_not_called()

    def test_execute_queues_next_stage(self) -> None:
        """Test that next stage is queued after completion."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_queue = MagicMock()
        mock_clock = MagicMock()
        mock_uow = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        job.stages[Stage.TRANSCODE] = StageStatus.RUNNING
        mock_job_repo.lock_job.return_value = job

        use_case = HandleStageCompleted(mock_job_repo, mock_queue, mock_clock, mock_uow)
        use_case.execute(video_id, Stage.TRANSCODE, [])

        # Should queue POSE stage
        mock_queue.publish.assert_called_once_with(
            stage=Stage.POSE,
            video_id=video_id,
            idempotency_key=f"{video_id}:{Stage.POSE.value}",
        )
        mock_uow.commit.assert_called_once()

    def test_execute_finalizes_on_last_stage(self) -> None:
        """Test that analysis is finalized when FEEDBACK stage completes."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_queue = MagicMock()
        mock_clock = MagicMock()
        mock_uow = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        job.stages[Stage.TRANSCODE] = StageStatus.DONE
        job.stages[Stage.POSE] = StageStatus.DONE
        job.stages[Stage.FEATURES] = StageStatus.DONE
        job.stages[Stage.FEEDBACK] = StageStatus.RUNNING
        mock_job_repo.lock_job.return_value = job

        use_case = HandleStageCompleted(mock_job_repo, mock_queue, mock_clock, mock_uow)
        use_case.execute(video_id, Stage.FEEDBACK, [])

        # Should finalize job directly (not call finalize_analysis.execute)
        assert job.status == AnalysisJobStatus.SUCCEEDED
        mock_queue.publish.assert_not_called()
        mock_uow.commit.assert_called_once()


class TestFinalizeAnalysis:
    """Tests for FinalizeAnalysis use case."""

    def test_execute_finalizes_job(self) -> None:
        """Test that job is finalized when all stages are done."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_clock = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        # All stages done
        for stage in Stage:
            job.stages[stage] = StageStatus.DONE

        use_case = FinalizeAnalysis(mock_job_repo, mock_clock)
        use_case.execute(job)

        assert job.status == AnalysisJobStatus.SUCCEEDED
        mock_job_repo.save_job.assert_called_once_with(job)

    def test_execute_raises_error_if_stages_not_done(self) -> None:
        """Test that error is raised if not all stages are done."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_clock = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        job.stages[Stage.TRANSCODE] = StageStatus.DONE
        job.stages[Stage.POSE] = StageStatus.RUNNING  # Not done

        use_case = FinalizeAnalysis(mock_job_repo, mock_clock)

        with pytest.raises(ValueError, match="Cannot finalize"):
            use_case.execute(job)


class TestFailAnalysis:
    """Tests for FailAnalysis use case."""

    def test_execute_marks_stage_and_job_as_failed(self) -> None:
        """Test that stage and job are marked as failed."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_clock = MagicMock()
        mock_uow = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        job.stages[Stage.TRANSCODE] = StageStatus.RUNNING
        mock_job_repo.lock_job.return_value = job

        use_case = FailAnalysis(mock_job_repo, mock_clock, mock_uow)
        use_case.execute(video_id, Stage.TRANSCODE, "Test error")

        assert job.stages[Stage.TRANSCODE] == StageStatus.FAILED
        assert job.status == AnalysisJobStatus.FAILED
        assert job.error_message == "Test error"
        mock_job_repo.save_job.assert_called_once_with(job)
        mock_uow.commit.assert_called_once()


class TestGetAnalysisStatus:
    """Tests for GetAnalysisStatus use case."""

    def test_execute_returns_job(self) -> None:
        """Test that job is returned if found."""
        video_id = uuid4()
        mock_job_repo = MagicMock()

        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.RUNNING,
        )
        mock_job_repo.get_job.return_value = job

        use_case = GetAnalysisStatus(mock_job_repo)
        result = use_case.execute(video_id)

        assert result is job
        mock_job_repo.get_job.assert_called_once_with(video_id)

    def test_execute_returns_none_if_not_found(self) -> None:
        """Test that None is returned if job not found."""
        video_id = uuid4()
        mock_job_repo = MagicMock()
        mock_job_repo.get_job.return_value = None

        use_case = GetAnalysisStatus(mock_job_repo)
        result = use_case.execute(video_id)

        assert result is None
