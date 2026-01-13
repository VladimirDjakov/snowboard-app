"""Local filesystem storage backend implementation."""

from pathlib import Path
from urllib.parse import quote

from backend.app.application.interfaces.storage import PresignedUploadUrl
from backend.app.infrastructure.storage.base import BaseStorage


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
        storage_path: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUploadUrl:
        """
        Generate upload URL for local storage.

        For local storage, returns an API endpoint that will be implemented later.
        Currently returns a placeholder URL.

        Args:
            storage_path: Storage path to the artifact
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds (ignored for local storage)

        Returns:
            PresignedUploadUrl with API endpoint URL
        """
        # Ensure directory exists for the file
        self._ensure_directory(storage_path)

        # Generate API endpoint URL (placeholder, will be implemented in API routes)
        url = f"{self.api_base_url}/api/v1/files/{quote(storage_path, safe='')}"

        return PresignedUploadUrl(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
            storage_path=storage_path,
            expires_in_sec=expires_in,
        )

    def generate_download_url(
        self,
        storage_path: str,
        expires_in: int,
    ) -> str:
        """
        Generate download URL for local storage.

        Args:
            storage_path: Storage path to the artifact
            expires_in: URL expiration time in seconds (ignored for local storage)

        Returns:
            API endpoint URL for downloading the file
        """
        return f"{self.api_base_url}/api/v1/files/{quote(storage_path, safe='')}"

    def exists(self, storage_path: str) -> bool:
        """
        Check if file exists in local storage.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            True if file exists, False otherwise
        """
        file_path = self._get_file_path(storage_path)
        return file_path.exists() and file_path.is_file()

    def delete(self, storage_path: str) -> None:
        """
        Delete file from local storage.

        Args:
            storage_path: Storage path to the artifact

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If deletion is not allowed
        """
        file_path = self._get_file_path(storage_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {storage_path}")

        file_path.unlink()

    def _get_file_path(self, storage_path: str) -> Path:
        """
        Get full file path for storage path.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            Full Path object
        """
        # Normalize path to prevent directory traversal
        normalized_key = storage_path.lstrip("/")
        return self.base_path.joinpath(normalized_key)

    def read_file(self, storage_path: str) -> bytes:
        """
        Read file from local storage.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = self._get_file_path(storage_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {storage_path}")

        return file_path.read_bytes()

    def write_file(
        self,
        storage_path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write file to local storage.

        Args:
            storage_path: Storage path to the artifact
            data: File contents as bytes
            content_type: MIME type (ignored for local storage, kept for interface compatibility)
        """
        # Ensure directory exists
        self._ensure_directory(storage_path)

        file_path = self._get_file_path(storage_path)
        file_path.write_bytes(data)

    def get_file_path(self, storage_path: str) -> Path | None:
        """
        Get local file path.

        For local storage, returns the full Path to the file.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            Path object pointing to the file
        """
        return self._get_file_path(storage_path)

    def _ensure_directory(self, storage_path: str) -> None:
        """
        Ensure directory exists for the given storage path.

        Args:
            storage_path: Storage path to the artifact
        """
        file_path = self._get_file_path(storage_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
