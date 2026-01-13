"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.application.interfaces.storage import PresignedUploadUrl


class BaseStorage(ABC):
    """Abstract interface for storage backends."""

    @abstractmethod
    def generate_upload_url(
        self,
        storage_path: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUploadUrl:
        """
        Generate a presigned URL for uploading a file.

        Args:
            storage_path: Storage path to the artifact (e.g., 'raw/{video_id}/original.mp4')
            content_type: MIME type of the file (e.g., 'video/mp4')
            expires_in: URL expiration time in seconds

        Returns:
            PresignedUploadUrl with method, URL, headers, storage_path, and expires_in_sec
        """
        pass

    @abstractmethod
    def generate_download_url(
        self,
        storage_path: str,
        expires_in: int,
    ) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            storage_path: Storage path to the artifact
            expires_in: URL expiration time in seconds

        Returns:
            URL string for downloading the file
        """
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """
        Delete a file from storage.

        Args:
            storage_path: Storage path to the artifact

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If deletion is not allowed
        """
        pass

    @abstractmethod
    def read_file(self, storage_path: str) -> bytes:
        """
        Read file from storage.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        pass

    @abstractmethod
    def write_file(
        self,
        storage_path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write file to storage.

        Args:
            storage_path: Storage path to the artifact
            data: File contents as bytes
            content_type: MIME type of the file (optional, used for S3)
        """
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> Path | None:
        """
        Get local file path if available.

        For local storage, returns the full Path to the file.
        For S3 storage, returns None.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            Path object for local storage, None for S3
        """
        pass
