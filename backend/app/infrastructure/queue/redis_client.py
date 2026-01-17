"""Redis client for connection management."""

import logging
from typing import Protocol

import redis
from redis.exceptions import ConnectionError, RedisError

logger = logging.getLogger(__name__)


class RedisConfig(Protocol):
    """Protocol for Redis configuration."""

    redis_url: str


class RedisClient:
    """Redis client for connection management with dependency injection."""

    def __init__(self, config: RedisConfig) -> None:
        """
        Initialize Redis client.

        Args:
            config: Configuration object with redis_url attribute
        """
        self._config = config
        self._connection: redis.Redis | None = None
        self._logger = logging.getLogger(__name__)

    def get_connection(self) -> redis.Redis:
        """
        Get Redis connection instance (lazy initialization).

        Creates and caches a Redis connection on first call.
        Subsequent calls return the cached connection.

        Returns:
            Redis connection instance

        Raises:
            ConnectionError: If unable to connect to Redis
            RedisError: For other Redis-related errors
        """
        if self._connection is None:
            try:
                self._logger.info(
                    "Creating Redis connection", extra={"redis_url": self._config.redis_url}
                )
                self._connection = redis.from_url(
                    self._config.redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )

                # Test connection with ping
                self._connection.ping()
                self._logger.info("Redis connection established successfully")
            except (ConnectionError, RedisError) as e:
                self._logger.error(
                    "Failed to connect to Redis",
                    extra={"error": str(e), "redis_url": self._config.redis_url},
                )
                raise

        return self._connection

    def check_health(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            conn = self.get_connection()
            conn.ping()
            return True
        except (ConnectionError, RedisError) as e:
            self._logger.warning("Redis health check failed", extra={"error": str(e)})
            return False

    def close(self) -> None:
        """Close Redis connection if it exists."""
        if self._connection is not None:
            try:
                self._connection.close()
                self._logger.info("Redis connection closed")
            except Exception as e:
                self._logger.warning("Error closing Redis connection", extra={"error": str(e)})
            finally:
                self._connection = None
