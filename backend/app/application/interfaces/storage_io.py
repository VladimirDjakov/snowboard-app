"""Storage file materialization helpers port for application layer."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageIO(Protocol):
    """Abstraction for local-file operations backed by object storage."""

    def materialize_from_storage(self, storage_path: str, *, base_dir: Path) -> Path:
        """
        Ensure a storage object is available as a local file path.

        Returns a direct local storage path when available, otherwise downloads
        bytes into the provided temporary base directory.
        """
        ...

    def prepare_output_path(
        self,
        storage_path: str,
        *,
        base_dir: Path,
        default_filename: str,
    ) -> tuple[Path, bool]:
        """
        Resolve where to write output before uploading to storage.

        Returns:
            (output_path, needs_upload)
        """
        ...

    def upload_to_storage(
        self,
        storage_path: str,
        file_path: Path,
        *,
        content_type: str | None = None,
    ) -> None:
        """Upload a local file to storage."""
        ...
