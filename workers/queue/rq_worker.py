"""RQ worker entrypoint for processing tasks from queues."""

import argparse
import logging
import os
import signal
import sys
from typing import NoReturn, Protocol

import redis
from rq import Queue, Worker
from rq.exceptions import RedisConnectionError

# Configure logging before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class RedisConfig(Protocol):
    """Protocol for Redis configuration."""

    redis_url: str


class WorkerConfig:
    """Configuration for RQ worker."""

    def __init__(
        self,
        queue_name: str,
        redis_url: str | None = None,
        verbose: bool = False,
    ) -> None:
        """
        Initialize worker configuration.

        Args:
            queue_name: Name of the queue to process
            redis_url: Redis connection URL (default: from REDIS_URL env var)
            verbose: Enable verbose logging
        """
        if queue_name not in ("cpu", "gpu"):
            raise ValueError(f"Invalid queue name: {queue_name}. Must be 'cpu' or 'gpu'")

        self.queue_name = queue_name
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.verbose = verbose


class WorkerManager:
    """Manager for RQ worker lifecycle."""

    def __init__(self, config: WorkerConfig) -> None:
        """
        Initialize worker manager.

        Args:
            config: Worker configuration
        """
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._worker: Worker | None = None
        self._redis_conn: redis.Redis[str] | None = None

    def setup_logging(self) -> None:
        """Configure logging for the worker."""
        level = logging.DEBUG if self._config.verbose else logging.INFO
        logging.getLogger().setLevel(level)
        logging.getLogger("rq.worker").setLevel(level)

    def create_redis_connection(self) -> redis.Redis[str]:
        """
        Create Redis connection.

        Returns:
            Redis connection instance

        Raises:
            SystemExit: If connection fails
        """
        self._logger.info(
            "Connecting to Redis", extra={"redis_url": self._config.redis_url, "queue": self._config.queue_name}
        )

        try:
            conn = redis.from_url(
                self._config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            conn.ping()
            self._logger.info("Redis connection established")
            self._redis_conn = conn
            return conn

        except (redis.ConnectionError, redis.RedisError) as e:
            self._logger.error(
                "Failed to connect to Redis", extra={"error": str(e), "redis_url": self._config.redis_url}
            )
            sys.exit(1)

    def create_worker(self) -> Worker:
        """
        Create RQ worker instance.

        Returns:
            RQ Worker instance
        """
        if self._redis_conn is None:
            self.create_redis_connection()

        queue = Queue(name=self._config.queue_name, connection=self._redis_conn)
        worker = Worker([queue], connection=self._redis_conn, name=f"worker-{self._config.queue_name}")

        self._logger.info("Worker created", extra={"queue": self._config.queue_name, "worker_name": worker.name})
        self._worker = worker
        return worker

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

        self._logger.info("Worker started, waiting for jobs...", extra={"queue": self._config.queue_name})

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
        if self._redis_conn is not None:
            try:
                self._redis_conn.close()
            except Exception as e:
                self._logger.warning("Error closing Redis connection", extra={"error": str(e)})


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="RQ worker for video processing tasks")
    parser.add_argument(
        "queue",
        choices=["cpu", "gpu"],
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


def main() -> NoReturn:
    """Main entrypoint for RQ worker."""
    args = parse_args()

    try:
        config = WorkerConfig(
            queue_name=args.queue,
            redis_url=args.redis_url,
            verbose=args.verbose,
        )

        manager = WorkerManager(config)
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
        logger.info("Worker stopped")

    sys.exit(0)


if __name__ == "__main__":
    main()
