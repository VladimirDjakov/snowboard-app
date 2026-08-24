"""Tests for RedisQueue adapter."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from rq import Queue
from rq.job import Job

from backend.app.domain.analysis_job import Stage
from backend.app.infrastructure.queue.redis_queue import QueueName, RedisQueue
from backend.app.presentation.workers.rq.task_registry import TASK_MAP


class TestRedisQueue:
    """Tests for RedisQueue class."""

    def test_publish_enqueues_transcode_on_cpu_queue(self):
        """Publish transcode stage enqueues to CPU queue."""
        with patch("backend.app.infrastructure.queue.redis_queue.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "job-1"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            queue = RedisQueue(mock_conn, TASK_MAP)
            video_id = uuid4()

            job_id = queue.publish(Stage.TRANSCODE, video_id)

            assert job_id == "job-1"
            mock_queue_class.assert_called_once_with(name=QueueName.CPU.value, connection=mock_conn)
            mock_queue.enqueue.assert_called_once_with(
                "backend.app.presentation.workers.rq.handlers.transcode_task",
                str(video_id),
            )

    def test_publish_enqueues_pose_on_gpu_queue(self):
        """Publish pose stage enqueues to GPU queue."""
        with patch("backend.app.infrastructure.queue.redis_queue.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "job-2"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            queue = RedisQueue(mock_conn, TASK_MAP)
            video_id = uuid4()

            job_id = queue.publish(Stage.POSE, video_id)

            assert job_id == "job-2"
            mock_queue_class.assert_called_once_with(name=QueueName.GPU.value, connection=mock_conn)
            mock_queue.enqueue.assert_called_once_with(
                "backend.app.presentation.workers.rq.handlers.pose_task", str(video_id)
            )

    def test_publish_reuses_queue_instance_for_same_queue(self):
        """Same queue name reuses cached Queue instance."""
        with patch("backend.app.infrastructure.queue.redis_queue.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "job-3"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            queue = RedisQueue(mock_conn, TASK_MAP)
            video_id = uuid4()

            queue.publish(Stage.TRANSCODE, video_id)
            queue.publish(Stage.FEATURES, video_id)

            mock_queue_class.assert_called_once_with(name=QueueName.CPU.value, connection=mock_conn)
            assert mock_queue.enqueue.call_count == 2

    def test_publish_creates_separate_queues_for_cpu_and_gpu(self):
        """Different queue names create separate Queue instances."""
        with patch("backend.app.infrastructure.queue.redis_queue.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "job-4"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            queue = RedisQueue(mock_conn, TASK_MAP)
            video_id = uuid4()

            queue.publish(Stage.TRANSCODE, video_id)
            queue.publish(Stage.POSE, video_id)

            assert mock_queue_class.call_count == 2
