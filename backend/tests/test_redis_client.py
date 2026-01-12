"""Tests for Redis client."""

from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError, RedisError

from backend.app.clients import redis as redis_module


class TestGetRedisConnection:
    """Tests for get_redis_connection function."""

    def test_creates_connection_on_first_call(self):
        """Test that connection is created on first call."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            conn = redis_module.get_redis_connection()

            assert conn is not None
            mock_from_url.assert_called_once()
            mock_conn.ping.assert_called_once()

    def test_returns_cached_connection_on_subsequent_calls(self):
        """Test that subsequent calls return cached connection."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            # First call
            conn1 = redis_module.get_redis_connection()
            # Second call
            conn2 = redis_module.get_redis_connection()

            assert conn1 is conn2
            # from_url should be called only once
            assert mock_from_url.call_count == 1

    def test_raises_connection_error_on_failed_connection(self):
        """Test that ConnectionError is raised on failed connection."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_from_url.side_effect = ConnectionError("Connection failed")

            with pytest.raises(ConnectionError, match="Connection failed"):
                redis_module.get_redis_connection()

    def test_raises_redis_error_on_ping_failure(self):
        """Test that RedisError is raised when ping fails."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_conn

            with pytest.raises(RedisError, match="Ping failed"):
                redis_module.get_redis_connection()

    def test_uses_correct_redis_url_from_settings(self):
        """Test that correct Redis URL is used from settings."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            test_url = "redis://test-host:6380/1"
            mock_settings.redis_url = test_url
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            redis_module.get_redis_connection()

            mock_from_url.assert_called_once_with(
                test_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )


class TestCheckRedisHealth:
    """Tests for check_redis_health function."""

    def test_returns_true_when_redis_is_healthy(self):
        """Test that health check returns True when Redis is healthy."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.return_value = True
            mock_from_url.return_value = mock_conn

            result = redis_module.check_redis_health()

            assert result is True
            # ping() is called twice: once in get_connection() and once in check_health()
            assert mock_conn.ping.call_count >= 1

    def test_returns_false_on_connection_error(self):
        """Test that health check returns False on ConnectionError."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_from_url.side_effect = ConnectionError("Connection failed")

            result = redis_module.check_redis_health()

            assert result is False

    def test_returns_false_on_redis_error(self):
        """Test that health check returns False on RedisError."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_conn

            result = redis_module.check_redis_health()

            assert result is False

    def test_returns_false_on_ping_failure(self):
        """Test that health check returns False when ping fails."""
        # Reset singleton
        redis_module._redis_client = None

        with (
            patch("backend.app.clients.redis.redis.from_url") as mock_from_url,
            patch("backend.app.core.config.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_conn.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_conn

            result = redis_module.check_redis_health()

            assert result is False
