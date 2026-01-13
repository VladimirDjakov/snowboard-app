"""Redis adapter for Queue port."""

from typing import Any
from uuid import UUID

from backend.app.adapters.redis.queue_client import QueueClient, QueueName
from backend.app.domain.analysis_job import Stage


class RedisQueue:
    """Redis implementation of Queue port."""

    def __init__(self, queue_client: QueueClient) -> None:
        """
        Initialize queue adapter.

        Args:
            queue_client: QueueClient instance
        """
        self._queue_client = queue_client

    def publish(
        self,
        stage: Stage,
        video_id: UUID,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Publish a task to the queue."""
        # Map Stage to QueueName
        queue_name = self._map_stage_to_queue(stage)

        # Map Stage to task function path
        task_func = self._map_stage_to_task(stage)

        # Generate idempotency key if not provided
        if idempotency_key is None:
            idempotency_key = f"{video_id}:{stage.value}"

        # Enqueue task
        job = self._queue_client.enqueue_task(
            queue_name,
            task_func,
            str(video_id),
        )

        return job.id

    @staticmethod
    def _map_stage_to_queue(stage: Stage) -> QueueName:
        """Map domain Stage to QueueName."""
        # CPU queue: TRANSCODE, FEATURES, FEEDBACK
        # GPU queue: POSE
        if stage == Stage.POSE:
            return QueueName.GPU
        return QueueName.CPU

    @staticmethod
    def _map_stage_to_task(stage: Stage) -> str:
        """Map domain Stage to task function path."""
        mapping = {
            Stage.TRANSCODE: "workers.queue.tasks.transcode_task",
            Stage.POSE: "workers.queue.tasks.pose_task",
            Stage.FEATURES: "workers.queue.tasks.features_task",
            Stage.FEEDBACK: "workers.queue.tasks.feedback_task",
        }
        return mapping[stage]
