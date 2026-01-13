"""Local filesystem storage backend implementation."""

from pathlib import Path
from urllib.parse import quote

from backend.app.adapters.storage.base import BaseStorage
from backend.app.application.ports.storage import PresignedUploadUrl


class LocalStorage(BaseStorage):
    """Local filesystem storage backend for MVP."""

    def __init__(self, storage_path: str | Path, api_base_url: str = "http://localhost:8000"):
        """
        Initialize local storage backend.

        Args:
            storage_path: Base path for storage (e.g., 'runtime/storage')
            api_base_url: Base URL for API endpoints (for generating download URLs)
        """
        self.base_path = Path(storage_path).resolve()
        self.api_base_url = api_base_url.rstrip("/")

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

    def generate_upload_url(
        self,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUploadUrl:
        """
        Generate upload URL for local storage.

        For local storage, returns an API endpoint that will be implemented later.
        Currently returns a placeholder URL.

        Args:
            object_key: Storage object key
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds (ignored for local storage)

        Returns:
            PresignedUploadUrl with API endpoint URL
        """
        # Ensure directory exists for the file
        self._ensure_directory(object_key)

        # Generate API endpoint URL (placeholder, will be implemented in API routes)
        url = f"{self.api_base_url}/api/v1/files/{quote(object_key, safe='')}"

        return PresignedUploadUrl(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
            object_key=object_key,
            expires_in_sec=expires_in,
        )

    def generate_download_url(
        self,
        object_key: str,
        expires_in: int,
    ) -> str:
        """
        Generate download URL for local storage.

        Args:
            object_key: Storage object key
            expires_in: URL expiration time in seconds (ignored for local storage)

        Returns:
            API endpoint URL for downloading the file
        """
        return f"{self.api_base_url}/api/v1/files/{quote(object_key, safe='')}"

    def exists(self, object_key: str) -> bool:
        """
        Check if file exists in local storage.

        Args:
            object_key: Storage object key

        Returns:
            True if file exists, False otherwise
        """
        file_path = self._get_file_path(object_key)
        return file_path.exists() and file_path.is_file()

    def delete(self, object_key: str) -> None:
        """
        Delete file from local storage.

        Args:
            object_key: Storage object key

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If deletion is not allowed
        """
        file_path = self._get_file_path(object_key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {object_key}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {object_key}")

        file_path.unlink()

    def _get_file_path(self, object_key: str) -> Path:
        """
        Get full file path for object key.

        Args:
            object_key: Storage object key

        Returns:
            Full Path object
        """
        # Normalize path to prevent directory traversal
        normalized_key = object_key.lstrip("/")
        return self.base_path.joinpath(normalized_key)

    def read_file(self, object_key: str) -> bytes:
        """
        Read file from local storage.

        Args:
            object_key: Storage object key

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = self._get_file_path(object_key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {object_key}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {object_key}")

        return file_path.read_bytes()

    def write_file(
        self,
        object_key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write file to local storage.

        Args:
            object_key: Storage object key
            data: File contents as bytes
            content_type: MIME type (ignored for local storage, kept for interface compatibility)
        """
        # Ensure directory exists
        self._ensure_directory(object_key)

        file_path = self._get_file_path(object_key)
        file_path.write_bytes(data)

    def get_file_path(self, object_key: str) -> Path:
        """
        Get local file path.

        For local storage, returns the full Path to the file.

        Args:
            object_key: Storage object key

        Returns:
            Path object pointing to the file
        """
        return self._get_file_path(object_key)

    def _ensure_directory(self, object_key: str) -> None:
        """
        Ensure directory exists for the given object key.

        Args:
            object_key: Storage object key
        """
        file_path = self._get_file_path(object_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
