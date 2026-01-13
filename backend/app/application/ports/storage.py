"""Unified storage port combining artifact operations and presigned URLs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PresignedUploadUrl:
    """Presigned upload URL + required request metadata."""

    method: str
    url: str
    headers: dict[str, str]
    object_key: str
    expires_in_sec: int


class Storage(Protocol):
    """Unified interface for storage operations."""

    # Artifact operations
    def exists(self, object_key: str) -> bool:
        """
        Check if artifact exists.

        Args:
            object_key: Storage object key

        Returns:
            True if exists, False otherwise
        """
        ...

    def read_file(self, object_key: str) -> bytes:
        """
        Read artifact file.

        Args:
            object_key: Storage object key

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        ...

    def write_file(
        self,
        object_key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write artifact file.

        Args:
            object_key: Storage object key
            data: File contents as bytes
            content_type: Optional MIME type
        """
        ...

    def delete(self, object_key: str) -> None:
        """
        Delete artifact file.

        Args:
            object_key: Storage object key

        Raises:
            FileNotFoundError: If file does not exist
        """
        ...

    def generate_upload_url(
        self,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUploadUrl:
        """
        Generate a presigned URL for uploading an object.

        Args:
            object_key: Storage object key
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds

        Returns:
            PresignedUploadUrl with method, URL, headers, object_key, and expires_in_sec
        """
        ...

    def generate_download_url(
        self,
        object_key: str,
        expires_in: int,
    ) -> str:
        """
        Generate a presigned URL for downloading an object.

        Args:
            object_key: Storage object key
            expires_in: URL expiration time in seconds

        Returns:
            URL string for downloading the file
        """
        ...

    def get_file_path(self, object_key: str) -> Path:
        """
        Get local file path if available.

        For local storage, returns the full Path to the file.
        For S3 storage, raises NotImplementedError.

        Args:
            object_key: Storage object key

        Returns:
            Path object for local storage

        Raises:
            NotImplementedError: For remote storage backends
        """
        ...
