"""RQ queue client for task enqueueing."""

import logging
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from rq import Queue
from rq.job import Job

logger = logging.getLogger(__name__)


class QueueName(str, Enum):
    """Queue name enumeration."""

    CPU = "cpu"
    GPU = "gpu"


class RedisConnection(Protocol):
    """Protocol for Redis connection."""

    def ping(self) -> bool:
        """Ping Redis server."""
        ...


class QueueClient:
    """Client for enqueueing tasks to RQ queues."""

    def __init__(self, redis_conn: RedisConnection) -> None:
        """
        Initialize queue client with Redis connection.

        Args:
            redis_conn: Redis connection instance
        """
        self._redis_conn = redis_conn
        self._logger = logging.getLogger(__name__)
        self._queues: dict[QueueName, Queue] = {}

    def _get_queue(self, queue_name: QueueName) -> Queue:
        """
        Get or create queue instance (cached).

        Args:
            queue_name: Queue name enum

        Returns:
            RQ Queue instance
        """
        if queue_name not in self._queues:
            self._queues[queue_name] = Queue(name=queue_name.value, connection=self._redis_conn)
        return self._queues[queue_name]

    def enqueue_task(
        self,
        queue_name: QueueName,
        task_func: str | Any,
        *args: Any,
        **kwargs: Any,
    ) -> Job:
        """
        Enqueue a task to the specified queue.

        Args:
            queue_name: Queue name enum (CPU or GPU)
            task_func: Task function (callable or string path like
                'workers.queue.tasks.transcode_task')
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            RQ Job instance

        Raises:
            ValueError: If queue_name is invalid
            rq.exceptions.InvalidJobOperation: If task cannot be enqueued
        """
        queue = self._get_queue(queue_name)

        # Enqueue task (RQ will import string paths automatically)
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

    def enqueue_transcode_task(self, video_id: UUID) -> Job:
        """
        Enqueue transcode task for a video.

        Args:
            video_id: UUID of the video to transcode

        Returns:
            RQ Job instance
        """
        return self.enqueue_task(
            QueueName.CPU,
            "workers.queue.tasks.transcode_task",
            str(video_id),
        )

    def enqueue_pose_task(self, video_id: UUID) -> Job:
        """
        Enqueue pose inference task for a video.

        Args:
            video_id: UUID of the video to process

        Returns:
            RQ Job instance
        """
        return self.enqueue_task(
            QueueName.GPU,
            "workers.queue.tasks.pose_task",
            str(video_id),
        )

    def enqueue_features_task(self, video_id: UUID) -> Job:
        """
        Enqueue features extraction task for a video.

        Args:
            video_id: UUID of the video to process

        Returns:
            RQ Job instance
        """
        return self.enqueue_task(
            QueueName.CPU,
            "workers.queue.tasks.features_task",
            str(video_id),
        )

    def enqueue_feedback_task(self, video_id: UUID) -> Job:
        """
        Enqueue feedback generation task for a video.

        Args:
            video_id: UUID of the video to process

        Returns:
            RQ Job instance
        """
        return self.enqueue_task(
            QueueName.CPU,
            "workers.queue.tasks.feedback_task",
            str(video_id),
        )


# Singleton instance for backward compatibility
_queue_client: QueueClient | None = None


def get_queue_client() -> QueueClient:
    """
    Get queue client instance (singleton pattern, backward compatibility).

    Returns:
        QueueClient instance
    """
    global _queue_client

    if _queue_client is None:
        from backend.app.clients.redis import get_redis_connection

        _queue_client = QueueClient(get_redis_connection())

    return _queue_client
