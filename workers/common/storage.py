"""Storage service helper for workers."""

from backend.app.core.config import settings
from backend.app.storage import create_storage_backend
from backend.app.storage.base import BaseStorage

# Singleton instance
_storage_instance: BaseStorage | None = None


def get_storage() -> BaseStorage:
    """
    Get storage backend instance (singleton pattern).

    Creates storage backend on first call and caches it for subsequent calls.
    Uses the same storage backend as the API (LocalStorage or S3Storage).

    Returns:
        StorageBackend instance (BaseStorage interface)
    """
    global _storage_instance

    if _storage_instance is None:
        _storage_instance = create_storage_backend(settings)

    return _storage_instance
