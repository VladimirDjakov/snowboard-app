"""Pytest configuration and shared fixtures."""

from unittest.mock import MagicMock, patch

# Global patches to prevent real connections during imports
_patches = []


def pytest_configure(config):
    """
    Configure pytest hooks - runs before test collection.

    This sets up mocks before any test modules are imported.
    Note: Storage factory mocking is NOT applied globally to allow
    test_storage.py to test the real factory.
    """
    # Mock Settings to avoid reading real environment variables
    mock_settings = MagicMock()
    mock_settings.database_url = "postgresql://test:test@localhost/test"
    mock_settings.redis_url = "redis://localhost:6379/0"
    mock_settings.storage_backend = "local"
    mock_settings.storage_local_path = "/tmp/test_storage"
    mock_settings.api_host = "localhost"
    mock_settings.api_port = 8000
    mock_settings.database_echo = False

    # Mock Redis connection
    mock_redis_conn = MagicMock()
    mock_redis_conn.ping.return_value = True

    # Apply patches before imports (but NOT storage factory - let test_storage.py test it)
    _patches.extend(
        [
            patch("backend.app.composition.settings.load_settings", return_value=mock_settings),
            patch("backend.app.adapters.redis.client.redis.from_url", return_value=mock_redis_conn),
            patch(
                "backend.app.infrastructure.postgres.session.create_engine",
                return_value=MagicMock(),
            ),
        ]
    )

    # Start all patches
    for p in _patches:
        p.start()


def pytest_unconfigure(config):
    """Cleanup patches after tests."""
    for p in _patches:
        p.stop()
    _patches.clear()
