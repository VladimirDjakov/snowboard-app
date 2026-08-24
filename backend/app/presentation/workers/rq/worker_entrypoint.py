"""RQ worker entrypoint for processing tasks from queues."""

import argparse
import logging
import signal
import sys

import redis
from rq import Queue, Worker

from backend.app.infrastructure.logging import setup_logging
from backend.app.infrastructure.queue.redis_queue import QueueName
from backend.app.presentation.bootstrap.container import Container
from backend.app.presentation.bootstrap.settings import Settings, load_settings

logger = logging.getLogger(__name__)


class WorkerConfig:
    """Configuration for RQ worker."""

    def __init__(
        self,
        queue_name: str,
        verbose: bool = False,
    ) -> None:
        """
        Initialize worker configuration.

        Args:
            queue_name: Name of the queue to process
            verbose: Enable verbose logging
        """
        allowed = {queue.value for queue in QueueName}
        if queue_name not in allowed:
            raise ValueError(
                f"Invalid queue name: {queue_name}. Must be one of: {', '.join(sorted(allowed))}"
            )

        self.queue_name = queue_name
        self.verbose = verbose


class WorkerManager:
    """Manager for RQ worker lifecycle."""

    def __init__(self, config: WorkerConfig, settings: Settings) -> None:
        """
        Initialize worker manager.

        Args:
            config: Worker configuration
            settings: Application settings
        """
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._worker: Worker | None = None
        self._redis_conn: redis.Redis | None = None
        self._container = Container(settings)

    def setup_logging(self) -> None:
        """Configure logging for the worker."""
        level = logging.DEBUG if self._config.verbose else logging.INFO
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
        logging.getLogger("rq.worker").setLevel(level)

    def create_worker(self) -> None:
        """Create RQ worker instance."""
        if self._redis_conn is None:
            self._redis_conn = self._container.get_redis_connection()

        queue = Queue(name=self._config.queue_name, connection=self._redis_conn)
        worker = Worker(
            [queue], connection=self._redis_conn, name=f"worker-{self._config.queue_name}"
        )

        self._logger.info(
            "Worker created", extra={"queue": self._config.queue_name, "worker_name": worker.name}
        )
        self._worker = worker

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame: object) -> None:
            """Handle shutdown signals."""
            self._logger.info("Received shutdown signal", extra={"signal": signum})
            if self._worker is not None:
                self._worker.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self) -> None:
        """Start the worker (blocks until stopped)."""
        if self._worker is None:
            self.create_worker()

        self._logger.info(
            "Worker started, waiting for jobs...",
            extra={"queue": self._config.queue_name},
        )

        try:
            self._worker.work(with_scheduler=True)
        except KeyboardInterrupt:
            self._logger.info("Worker interrupted by user")
        except Exception as e:
            self._logger.error("Worker error", extra={"error": str(e)}, exc_info=True)
            raise

    def stop(self) -> None:
        """Stop the worker gracefully."""
        if self._worker is not None:
            self._worker.stop()
            self._logger.info("Worker stopped")

    def cleanup(self) -> None:
        """Cleanup resources."""
        self._container.close()


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="RQ worker for video processing tasks")
    parser.add_argument(
        "queue",
        choices=[queue.value for queue in QueueName],
        help="Queue name to process tasks from",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=None,
        help="Redis connection URL (default: from REDIS_URL env var)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entrypoint for RQ worker."""
    args = parse_args()
    manager: WorkerManager | None = None

    try:
        settings = load_settings()
        if args.redis_url:
            settings = settings.model_copy(update={"redis_url": args.redis_url})
        setup_logging(settings)
        config = WorkerConfig(
            queue_name=args.queue,
            verbose=args.verbose,
        )

        manager = WorkerManager(config, settings)
        manager.setup_logging()
        manager.create_worker()
        manager.setup_signal_handlers()

        logger.info("Starting RQ worker", extra={"queue": config.queue_name})

        manager.start()

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error("Worker error", extra={"error": str(e)}, exc_info=True)
        sys.exit(1)
    finally:
        if manager is not None:
            manager.cleanup()
        logger.info("Worker stopped")

    sys.exit(0)


if __name__ == "__main__":
    main()
