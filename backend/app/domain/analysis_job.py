"""Domain models for video analysis job."""

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class Stage(str, Enum):
    """Processing stages in the analysis pipeline."""

    TRANSCODE = "transcode"
    POSE = "pose"
    FEATURES = "features"
    FEEDBACK = "feedback"


class StageStatus(str, Enum):
    """Status of a processing stage."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AnalysisJobStatus(str, Enum):
    """Overall status of the analysis job."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class AnalysisJob:
    """Domain model for video analysis job with state machine and invariants."""

    video_id: UUID
    status: AnalysisJobStatus
    stages: dict[Stage, StageStatus] = field(default_factory=dict)
    version: int = field(default=1)  # For optimistic locking
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Initialize default stages if not provided."""
        if not self.stages:
            self.stages = dict.fromkeys(Stage, StageStatus.PENDING)

    def mark_stage_running(self, stage: Stage) -> None:
        """
        Mark a stage as running.

        Args:
            stage: Stage to mark as running

        Raises:
            ValueError: If stage transition is invalid
        """
        current_status = self.stages.get(stage)
        if current_status == StageStatus.DONE:
            # Idempotency: already done, no-op
            return
        if current_status not in (StageStatus.PENDING, StageStatus.QUEUED):
            raise ValueError(
                f"Cannot mark stage {stage.value} as RUNNING from {current_status.value}"
            )

        self.stages[stage] = StageStatus.RUNNING
        if self.status == AnalysisJobStatus.CREATED:
            self.status = AnalysisJobStatus.QUEUED
        if self.status == AnalysisJobStatus.QUEUED:
            self.status = AnalysisJobStatus.RUNNING
        self.version += 1

    def mark_stage_done(self, stage: Stage) -> None:
        """
        Mark a stage as done.

        Args:
            stage: Stage to mark as done

        Raises:
            ValueError: If stage transition is invalid or previous stages are not done
        """
        current_status = self.stages.get(stage)
        if current_status == StageStatus.DONE:
            # Idempotency: already done, no-op
            return
        if current_status != StageStatus.RUNNING:
            raise ValueError(f"Cannot mark stage {stage.value} as DONE from {current_status.value}")

        # Check that previous stages are done (invariant: stages complete in order)
        stage_order = [Stage.TRANSCODE, Stage.POSE, Stage.FEATURES, Stage.FEEDBACK]
        stage_index = stage_order.index(stage)
        for prev_stage in stage_order[:stage_index]:
            if self.stages.get(prev_stage) != StageStatus.DONE:
                raise ValueError(
                    f"Cannot mark {stage.value} as DONE: previous stage "
                    f"{prev_stage.value} is not DONE"
                )

        self.stages[stage] = StageStatus.DONE
        self.version += 1

    def mark_stage_failed(self, stage: Stage, reason: str) -> None:
        """
        Mark a stage as failed.

        Args:
            stage: Stage that failed
            reason: Error message describing the failure

        Raises:
            ValueError: If stage transition is invalid
        """
        current_status = self.stages.get(stage)
        if current_status == StageStatus.DONE:
            raise ValueError(f"Cannot mark stage {stage.value} as FAILED: already DONE")

        self.stages[stage] = StageStatus.FAILED
        self.status = AnalysisJobStatus.FAILED
        self.error_message = reason
        self.version += 1

    def can_finalize(self) -> bool:
        """
        Check if job can be finalized (all stages done).

        Returns:
            True if all stages are DONE
        """
        return all(status == StageStatus.DONE for status in self.stages.values())

    def finalize(self) -> None:
        """
        Finalize the job (mark as SUCCEEDED).

        Raises:
            ValueError: If not all stages are done (invariant: SUCCEEDED only after FEEDBACK)
        """
        if not self.can_finalize():
            raise ValueError("Cannot finalize: not all stages are DONE")
        if self.status == AnalysisJobStatus.FAILED:
            raise ValueError("Cannot finalize: job is in FAILED state")

        self.status = AnalysisJobStatus.SUCCEEDED
        self.version += 1
