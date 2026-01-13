"""Use case: Handle stage completion."""

from uuid import UUID

from backend.app.application.ports.clock import Clock
from backend.app.application.ports.job_repo import JobRepo
from backend.app.application.ports.queue import Queue
from backend.app.application.ports.uow import UnitOfWork
from backend.app.domain.analysis_job import Stage, StageStatus
from backend.app.domain.value_objects import ArtifactRef


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
        artifacts: list[ArtifactRef],
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
