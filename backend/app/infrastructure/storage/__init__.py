"""Storage adapters."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.presentation.bootstrap.settings import Settings
from backend.app.infrastructure.storage.base import BaseStorage
from backend.app.infrastructure.storage.local import LocalStorage
from backend.app.infrastructure.storage.s3 import S3Storage


def create_storage_backend(settings: "Settings") -> BaseStorage:
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


__all__ = ["create_storage_backend", "BaseStorage", "LocalStorage", "S3Storage"]
