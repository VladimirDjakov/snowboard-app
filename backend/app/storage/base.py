"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.api.schemas.videos import UploadInfo


class BaseStorage(ABC):
    """Abstract interface for storage backends."""

    @abstractmethod
    def generate_upload_url(
        self,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> UploadInfo:
        """
        Generate a presigned URL for uploading a file.

        Args:
            object_key: Storage object key (e.g., 'raw/{video_id}/original.mp4')
            content_type: MIME type of the file (e.g., 'video/mp4')
            expires_in: URL expiration time in seconds

        Returns:
            UploadInfo with method, URL, headers, object_key, and expires_in_sec
        """
        pass

    @abstractmethod
    def generate_download_url(
        self,
        object_key: str,
        expires_in: int,
    ) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            object_key: Storage object key
            expires_in: URL expiration time in seconds

        Returns:
            URL string for downloading the file
        """
        pass

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            object_key: Storage object key

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, object_key: str) -> None:
        """
        Delete a file from storage.

        Args:
            object_key: Storage object key

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If deletion is not allowed
        """
        pass

    @abstractmethod
    def read_file(self, object_key: str) -> bytes:
        """
        Read file from storage.

        Args:
            object_key: Storage object key

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        pass

    @abstractmethod
    def write_file(
        self,
        object_key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write file to storage.

        Args:
            object_key: Storage object key
            data: File contents as bytes
            content_type: MIME type of the file (optional, used for S3)
        """
        pass

    @abstractmethod
    def get_file_path(self, object_key: str) -> Path:
        """
        Get local file path if available.

        For local storage, returns the full Path to the file.
        For S3 storage, returns None.

        Args:
            object_key: Storage object key

        Returns:
            Path object for local storage, None for S3
        """
        pass
