"""Tests for Redis client."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError, RedisError

from backend.app.infrastructure.queue.redis_client import RedisClient


def make_config(redis_url: str = "redis://localhost:6379/0") -> SimpleNamespace:
    """Create a minimal config object for RedisClient."""
    return SimpleNamespace(redis_url=redis_url)


class TestRedisClientConnection:
    """Tests for RedisClient.get_connection."""

    def test_creates_connection_on_first_call(self):
        """Test that connection is created on first call."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config())
            conn = client.get_connection()

            assert conn is not None
            mock_from_url.assert_called_once()
            mock_conn.ping.assert_called_once()

    def test_returns_cached_connection_on_subsequent_calls(self):
        """Test that subsequent calls return cached connection."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config())
            conn1 = client.get_connection()
            conn2 = client.get_connection()

            assert conn1 is conn2
            assert mock_from_url.call_count == 1

    def test_raises_connection_error_on_failed_connection(self):
        """Test that ConnectionError is raised on failed connection."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.side_effect = ConnectionError("Connection failed")

            client = RedisClient(make_config())
            with pytest.raises(ConnectionError, match="Connection failed"):
                client.get_connection()

    def test_raises_redis_error_on_ping_failure(self):
        """Test that RedisError is raised when ping fails."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config())
            with pytest.raises(RedisError, match="Ping failed"):
                client.get_connection()

    def test_uses_correct_redis_url_from_config(self):
        """Test that correct Redis URL is used from config."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            test_url = "redis://test-host:6380/1"
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config(redis_url=test_url))
            client.get_connection()

            mock_from_url.assert_called_once_with(
                test_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )


class TestRedisClientHealth:
    """Tests for RedisClient.check_health."""

    def test_returns_true_when_redis_is_healthy(self):
        """Test that health check returns True when Redis is healthy."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config())
            result = client.check_health()

            assert result is True
            assert mock_conn.ping.call_count >= 1

    def test_returns_false_on_connection_error(self):
        """Test that health check returns False on ConnectionError."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.side_effect = ConnectionError("Connection failed")

            client = RedisClient(make_config())
            result = client.check_health()

            assert result is False

    def test_returns_false_on_redis_error(self):
        """Test that health check returns False on RedisError."""
        with patch("backend.app.infrastructure.queue.redis_client.redis.from_url") as mock_from_url:
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_conn

            client = RedisClient(make_config())
            result = client.check_health()

            assert result is False
