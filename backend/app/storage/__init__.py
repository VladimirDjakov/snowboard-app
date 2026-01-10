"""Storage backend factory."""

from backend.app.core.config import Settings
from backend.app.storage.base import BaseStorage
from backend.app.storage.local import LocalStorage
from backend.app.storage.s3 import S3Storage


def create_storage_backend(settings: Settings) -> BaseStorage:
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
