"""Use case: Start analysis pipeline."""

from uuid import UUID

from backend.app.application.ports.clock import Clock
from backend.app.application.ports.job_repo import JobRepo
from backend.app.application.ports.queue import Queue
from backend.app.application.ports.uow import UnitOfWork
from backend.app.domain.analysis_job import AnalysisJobStatus, Stage, StageStatus


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
