"""Use case: Fail analysis."""

from uuid import UUID

from backend.app.application.ports.clock import Clock
from backend.app.application.ports.job_repo import JobRepo
from backend.app.application.ports.uow import UnitOfWork
from backend.app.domain.analysis_job import Stage


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
