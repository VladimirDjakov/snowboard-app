"""Redis adapter for Queue port."""

import logging
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from rq import Queue
from rq.job import Job

from backend.app.domain.analysis_job import Stage


class QueueName(str, Enum):
    """Queue name enumeration."""

    CPU = "cpu"
    GPU = "gpu"


STAGE_TO_QUEUE: dict[Stage, QueueName] = {
    Stage.TRANSCODE: QueueName.CPU,
    Stage.POSE: QueueName.GPU,
    Stage.FEATURES: QueueName.CPU,
    Stage.FEEDBACK: QueueName.CPU,
}


class RedisConnection(Protocol):
    """Protocol for Redis connection."""

    def ping(self) -> bool:
        """Ping Redis server."""
        ...


class RedisQueue:
    """Redis implementation of Queue port."""

    def __init__(self, redis_conn: RedisConnection, task_map: dict[Stage, str]) -> None:
        """
        Initialize queue adapter.

        Args:
            redis_conn: Redis connection instance
            task_map: Mapping of Stage to task function path
        """
        self._redis_conn = redis_conn
        self._task_map = task_map
        self._logger = logging.getLogger(__name__)
        self._queues: dict[QueueName, Queue] = {}

    def _get_queue(self, queue_name: QueueName) -> Queue:
        """Get or create queue instance (cached)."""
        if queue_name not in self._queues:
            self._queues[queue_name] = Queue(name=queue_name.value, connection=self._redis_conn)
        return self._queues[queue_name]

    def _enqueue_task(
        self,
        queue_name: QueueName,
        task_func: str | Any,
        *args: Any,
        **kwargs: Any,
    ) -> Job:
        """Enqueue a task to the specified queue."""
        queue = self._get_queue(queue_name)
        job = queue.enqueue(task_func, *args, **kwargs)

        task_name = (
            task_func
            if isinstance(task_func, str)
            else getattr(task_func, "__name__", str(task_func))
        )
        self._logger.info(
            "Task enqueued",
            extra={
                "queue": queue_name.value,
                "job_id": job.id,
                "task": task_name,
            },
        )

        return job

    def publish(
        self,
        stage: Stage,
        video_id: UUID,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Publish a task to the queue."""
        # Map Stage to QueueName
        queue_name = STAGE_TO_QUEUE[stage]

        # Map Stage to task function path
        task_func = self._task_map[stage]

        # Generate idempotency key if not provided
        if idempotency_key is None:
            idempotency_key = f"{video_id}:{stage.value}"

        # Enqueue task
        job = self._enqueue_task(
            queue_name,
            task_func,
            str(video_id),
        )

        return job.id
