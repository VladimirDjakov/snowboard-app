"""Tests for RQ queue client."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from rq import Queue
from rq.exceptions import InvalidJobOperation
from rq.job import Job

from backend.app.adapters.redis import QueueClient
from backend.app.adapters.redis.queue_client import QueueName


class TestQueueClient:
    """Tests for QueueClient class."""

    def test_init_creates_redis_connection(self):
        """Test that __init__ creates Redis connection."""
        mock_conn = MagicMock()
        client = QueueClient(mock_conn)

        assert client._redis_conn is mock_conn

    def test_enqueue_task_with_valid_cpu_queue(self):
        """Test enqueue_task with valid CPU queue."""
        with (
            patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class,
            patch("backend.app.adapters.redis.queue_client.logging.getLogger") as mock_get_logger,
        ):
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "test-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            client = QueueClient(mock_conn)
            result = client.enqueue_task(QueueName.CPU, "test.task", "arg1", kwarg1="value1")

            assert result is mock_job
            mock_queue_class.assert_called_once_with(name=QueueName.CPU.value, connection=mock_conn)
            mock_queue.enqueue.assert_called_once_with("test.task", "arg1", kwarg1="value1")
            mock_logger.info.assert_called_once()

    def test_enqueue_task_with_valid_gpu_queue(self):
        """Test enqueue_task with valid GPU queue."""
        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "test-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_task(QueueName.GPU, "test.task")

            assert result is mock_job
            mock_queue_class.assert_called_once_with(name=QueueName.GPU.value, connection=mock_conn)

    def test_enqueue_task_raises_value_error_for_invalid_queue(self):
        """Test that enqueue_task raises ValueError for invalid queue name."""
        mock_conn = MagicMock()
        client = QueueClient(mock_conn)

        with pytest.raises(AttributeError, match="'str' object has no attribute 'value'"):
            client.enqueue_task("invalid_queue", "test.task")

    def test_enqueue_task_handles_callable_task_func(self):
        """Test enqueue_task with callable task function."""
        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()

            def test_task():
                pass

            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "test-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_task(QueueName.CPU, test_task)

            assert result is mock_job
            mock_queue.enqueue.assert_called_once_with(test_task)

    def test_enqueue_task_logs_correctly(self):
        """Test that enqueue_task logs correctly."""
        with (
            patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class,
            patch("backend.app.adapters.redis.queue_client.logging.getLogger") as mock_get_logger,
        ):
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "job-123"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            client = QueueClient(mock_conn)
            client.enqueue_task(QueueName.CPU, "test.task")

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Task enqueued" in call_args[0][0]
            assert call_args[1]["extra"]["queue"] == QueueName.CPU.value
            assert call_args[1]["extra"]["job_id"] == "job-123"
            assert call_args[1]["extra"]["task"] == "test.task"

    def test_enqueue_transcode_task(self):
        """Test enqueue_transcode_task helper method."""
        video_id = uuid4()

        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "transcode-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_transcode_task(video_id)

            assert result is mock_job
            mock_queue.enqueue.assert_called_once_with(
                "workers.queue.tasks.transcode_task", str(video_id)
            )

    def test_enqueue_pose_task(self):
        """Test enqueue_pose_task helper method."""
        video_id = uuid4()

        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "pose-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_pose_task(video_id)

            assert result is mock_job
            mock_queue_class.assert_called_once_with(name=QueueName.GPU.value, connection=mock_conn)
            mock_queue.enqueue.assert_called_once_with(
                "workers.queue.tasks.pose_task", str(video_id)
            )

    def test_enqueue_features_task(self):
        """Test enqueue_features_task helper method."""
        video_id = uuid4()

        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "features-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_features_task(video_id)

            assert result is mock_job
            mock_queue.enqueue.assert_called_once_with(
                "workers.queue.tasks.features_task", str(video_id)
            )

    def test_enqueue_feedback_task(self):
        """Test enqueue_feedback_task helper method."""
        video_id = uuid4()

        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_job = MagicMock(spec=Job)
            mock_job.id = "feedback-job-id"
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)
            result = client.enqueue_feedback_task(video_id)

            assert result is mock_job
            mock_queue.enqueue.assert_called_once_with(
                "workers.queue.tasks.feedback_task", str(video_id)
            )

    def test_enqueue_task_propagates_invalid_job_operation(self):
        """Test that InvalidJobOperation is propagated from queue.enqueue."""
        with patch("backend.app.adapters.redis.queue_client.Queue") as mock_queue_class:
            mock_conn = MagicMock()
            mock_queue = MagicMock(spec=Queue)
            mock_queue.enqueue.side_effect = InvalidJobOperation("Invalid job")
            mock_queue_class.return_value = mock_queue

            client = QueueClient(mock_conn)

            with pytest.raises(InvalidJobOperation, match="Invalid job"):
                client.enqueue_task(QueueName.CPU, "test.task")
