"""Interface for task queue."""

from typing import Any, Protocol
from uuid import UUID

from backend.app.domain.analysis_job import Stage


class Queue(Protocol):
    """Interface for task queue (generic, not pipeline-specific)."""

    def publish(
        self,
        stage: Stage,
        video_id: UUID,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """
        Publish a task to the queue.

        Args:
            stage: Processing stage
            video_id: Video identifier
            payload: Optional payload data
            idempotency_key: Optional idempotency key for deduplication

        Returns:
            Job/event ID
        """
        ...
