"""Storage adapters."""

from typing import Protocol

from backend.app.infrastructure.storage.base import BaseStorage
from backend.app.infrastructure.storage.local import LocalStorage
from backend.app.infrastructure.storage.s3 import S3Storage
from backend.app.infrastructure.storage.storage_io import DefaultStorageIO


class StorageSettings(Protocol):
    """Protocol for storage configuration."""

    storage_backend: str
    storage_local_path: str
    api_host: str
    api_port: int
    s3_endpoint_url: str | None
    s3_access_key_id: str | None
    s3_secret_access_key: str | None
    s3_bucket_name: str | None
    s3_region: str
    s3_presigned_url_expiry: int


def create_storage_backend(settings: StorageSettings) -> BaseStorage:
    """
    Create storage backend instance based on settings.

    Args:
        settings: Application settings

    Returns:
        StorageBackend instance (LocalStorageBackend or S3StorageBackend)

    Raises:
        ValueError: If storage_backend is not supported
    """
    if settings.storage_backend == "local":
        return LocalStorage(
            storage_path=settings.storage_local_path,
            api_base_url=f"http://{settings.api_host}:{settings.api_port}",
        )

    if settings.storage_backend == "s3":
        return S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            expires_in=settings.s3_presigned_url_expiry,
        )

    raise ValueError(f"Unsupported storage_backend: {settings.storage_backend}")


__all__ = [
    "create_storage_backend",
    "BaseStorage",
    "LocalStorage",
    "S3Storage",
    "DefaultStorageIO",
]
