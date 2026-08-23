"""Default implementation of application StorageIO port."""

from __future__ import annotations

from pathlib import Path

from backend.app.application.interfaces.storage import Storage
from backend.app.application.interfaces.storage_io import StorageIO


class DefaultStorageIO(StorageIO):
    """StorageIO backed by the generic Storage interface."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def materialize_from_storage(self, storage_path: str, *, base_dir: Path) -> Path:
        local_path = self._storage.get_file_path(storage_path)
        if local_path is not None and local_path.exists():
            return local_path

        target_path = base_dir.joinpath(storage_path)
        self._ensure_parent_dir(target_path)
        target_path.write_bytes(self._storage.read_file(storage_path))
        return target_path

    def prepare_output_path(
        self,
        storage_path: str,
        *,
        base_dir: Path,
        default_filename: str,
    ) -> tuple[Path, bool]:
        local_path = self._storage.get_file_path(storage_path)
        if local_path is None:
            target_path = base_dir.joinpath(default_filename)
            self._ensure_parent_dir(target_path)
            return target_path, True
        self._ensure_parent_dir(local_path)
        return local_path, False

    def upload_to_storage(
        self,
        storage_path: str,
        file_path: Path,
        *,
        content_type: str | None = None,
    ) -> None:
        self._storage.write_file(storage_path, file_path.read_bytes(), content_type=content_type)

    @staticmethod
    def _ensure_parent_dir(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
