"""Use cases for analysis pipeline management."""

from __future__ import annotations

from uuid import UUID

from backend.app.application.interfaces.clock import Clock
from backend.app.application.interfaces.job_repo import JobRepo
from backend.app.application.interfaces.queue import Queue
from backend.app.application.interfaces.uow import UnitOfWork
from backend.app.domain.analysis_job import AnalysisJob, AnalysisJobStatus, Stage, StageStatus
from backend.app.domain.value_objects import Artifact


class GetAnalysisStatus:
    """Use case for getting analysis job status (read-only)."""

    def __init__(self, job_repo: JobRepo) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
        """
        self._job_repo = job_repo

    def execute(self, video_id: UUID) -> AnalysisJob | None:
        """
        Get analysis job status.

        Args:
            video_id: Video identifier

        Returns:
            AnalysisJob if found, None otherwise
        """
        return self._job_repo.get_job(video_id)


class ListArtifacts:
    """Use case for listing artifacts for a video (read-only)."""

    def __init__(self, job_repo: JobRepo) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
        """
        self._job_repo = job_repo

    def execute(self, video_id: UUID) -> list[Artifact] | None:
        """
        Get list of artifacts for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of ArtifactRef if video found, None otherwise
        """
        return self._job_repo.get_artifacts(video_id)


class StartAnalysis:
    """Use case for starting video analysis pipeline."""

    def __init__(self, job_repo: JobRepo, queue: Queue, clock: Clock, uow: UnitOfWork) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            queue: Task queue
            clock: Clock for timestamps
            uow: Unit of Work for transaction management
        """
        self._job_repo = job_repo
        self._queue = queue
        self._clock = clock
        self._uow = uow

    def execute(self, video_id: UUID) -> None:
        """
        Start analysis pipeline for a video.

        Args:
            video_id: Video identifier

        Raises:
            ValueError: If job is not in CREATED status or other invariants violated
        """
        # Lock job for concurrent access
        job = self._job_repo.lock_job(video_id)
        if job is None:
            # Create job if it doesn't exist
            job = self._job_repo.create_job(video_id)

        # Check invariants: status must be CREATED
        if job.status != AnalysisJobStatus.CREATED:
            raise ValueError(
                f"Cannot start analysis: job is in {job.status.value} status, expected CREATED"
            )

        # Update status to QUEUED
        job.status = AnalysisJobStatus.QUEUED

        # Ensure all stages are initialized as PENDING
        for stage in Stage:
            if stage not in job.stages:
                job.stages[stage] = StageStatus.PENDING

        # Publish TRANSCODE stage to queue
        self._queue.publish(
            stage=Stage.TRANSCODE,
            video_id=video_id,
            idempotency_key=f"{video_id}:{Stage.TRANSCODE.value}",
        )

        # Mark TRANSCODE as QUEUED
        job.stages[Stage.TRANSCODE] = StageStatus.QUEUED

        # Update status to RUNNING
        job.status = AnalysisJobStatus.RUNNING

        # Save job
        self._job_repo.save_job(job)

        # Commit transaction
        self._uow.commit()


class HandleStageCompleted:
    """Use case for handling completion of a processing stage."""

    def __init__(
        self,
        job_repo: JobRepo,
        queue: Queue,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            queue: Task queue
            clock: Clock for timestamps
            uow: Unit of Work for transaction management
        """
        self._job_repo = job_repo
        self._queue = queue
        self._clock = clock
        self._uow = uow

    def execute(
        self,
        video_id: UUID,
        stage: Stage,
        artifacts: list[Artifact],
    ) -> None:
        """
        Handle completion of a processing stage.

        Args:
            video_id: Video identifier
            stage: Completed stage
            artifacts: List of artifacts produced by the stage

        Raises:
            ValueError: If stage transition is invalid
        """
        # Lock job for concurrent access
        job = self._job_repo.lock_job(video_id)
        if job is None:
            raise ValueError(f"Job not found for video {video_id}")

        # Check invariants: stage must be RUNNING
        current_status = job.stages.get(stage)
        if current_status != StageStatus.RUNNING:
            # Idempotency: if already DONE, no-op (don't save)
            if current_status == StageStatus.DONE:
                return
            raise ValueError(
                f"Cannot complete stage {stage.value}: current status is "
                f"{current_status.value}, expected RUNNING"
            )

        # Mark stage as DONE (domain method handles invariants)
        job.mark_stage_done(stage)

        # Register artifacts (not saving files - worker already did that)
        if artifacts:
            self._job_repo.register_artifacts(video_id, artifacts)

        # Check if this is the last stage (FEEDBACK)
        if stage == Stage.FEEDBACK:
            # Finalize analysis (job is already loaded and locked)
            job.finalize()
        else:
            # Queue next stage
            next_stage = self._get_next_stage(stage)
            if next_stage:
                self._queue.publish(
                    stage=next_stage,
                    video_id=video_id,
                    idempotency_key=f"{video_id}:{next_stage.value}",
                )
                # Mark next stage as QUEUED
                job.stages[next_stage] = StageStatus.QUEUED

        # Save job
        self._job_repo.save_job(job)

        # Commit transaction
        self._uow.commit()

    @staticmethod
    def _get_next_stage(current_stage: Stage) -> Stage | None:
        """Get next stage in pipeline."""
        stage_order = [Stage.TRANSCODE, Stage.POSE, Stage.FEATURES, Stage.FEEDBACK]
        try:
            current_index = stage_order.index(current_stage)
            if current_index < len(stage_order) - 1:
                return stage_order[current_index + 1]
        except ValueError:
            pass
        return None


class HandleStageStarted:
    """Use case for marking a processing stage as running."""

    def __init__(self, job_repo: JobRepo, uow: UnitOfWork) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            uow: Unit of Work for transaction management
        """
        self._job_repo = job_repo
        self._uow = uow

    def execute(self, video_id: UUID, stage: Stage) -> None:
        """
        Mark a stage as running.

        Args:
            video_id: Video identifier
            stage: Stage that is starting

        Raises:
            ValueError: If stage transition is invalid
        """
        job = self._job_repo.lock_job(video_id)
        if job is None:
            raise ValueError(f"Job not found for video {video_id}")

        current_status = job.stages.get(stage)
        if current_status in (StageStatus.RUNNING, StageStatus.DONE):
            return

        job.mark_stage_running(stage)
        self._job_repo.save_job(job)
        self._uow.commit()


class FailAnalysis:
    """Use case for failing analysis."""

    def __init__(self, job_repo: JobRepo, clock: Clock, uow: UnitOfWork) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            clock: Clock for timestamps
            uow: Unit of Work for transaction management
        """
        self._job_repo = job_repo
        self._clock = clock
        self._uow = uow

    def execute(self, video_id: UUID, stage: Stage, reason: str) -> None:
        """
        Fail analysis at a specific stage.

        Args:
            video_id: Video identifier
            stage: Stage that failed
            reason: Error message describing the failure

        Raises:
            ValueError: If stage transition is invalid
        """
        # Lock job for concurrent access
        job = self._job_repo.lock_job(video_id)
        if job is None:
            raise ValueError(f"Job not found for video {video_id}")

        # Mark stage as failed (domain method handles invariants)
        job.mark_stage_failed(stage, reason)

        # Save job
        self._job_repo.save_job(job)

        # Commit transaction
        self._uow.commit()


class FinalizeAnalysis:
    """Use case for finalizing completed analysis."""

    def __init__(self, job_repo: JobRepo, clock: Clock) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            clock: Clock for timestamps
        """
        self._job_repo = job_repo
        self._clock = clock

    def execute(self, job: AnalysisJob) -> None:
        """
        Finalize analysis (mark as DONE).

        Args:
            job: Analysis job to finalize (already loaded and locked)

        Raises:
            ValueError: If not all stages are done
        """
        # Finalize job (domain method checks invariants)
        job.finalize()

        # Save job (commit will be handled by UoW)
        self._job_repo.save_job(job)
