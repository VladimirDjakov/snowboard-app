"""Tests for storage-backed local file materialization."""

from pathlib import Path

from backend.app.infrastructure.storage.storage_io import DefaultStorageIO


class RemoteStorageStub:
    """In-memory remote storage with no direct filesystem paths."""

    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = objects or {}
        self.content_types: dict[str, str | None] = {}

    def get_file_path(self, storage_path: str) -> None:
        return None

    def read_file(self, storage_path: str) -> bytes:
        return self.objects[storage_path]

    def write_file(
        self,
        storage_path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        self.objects[storage_path] = data
        self.content_types[storage_path] = content_type


def test_remote_storage_is_materialized_and_output_is_uploaded(tmp_path: Path) -> None:
    input_key = "raw/video-id/original.mp4"
    output_key = "proc/video-id/keypoints_v1.jsonl"
    storage = RemoteStorageStub({input_key: b"video-bytes"})
    storage_io = DefaultStorageIO(storage)

    input_path = storage_io.materialize_from_storage(input_key, base_dir=tmp_path)
    output_path, needs_upload = storage_io.prepare_output_path(
        output_key,
        base_dir=tmp_path,
        default_filename="keypoints.jsonl",
    )
    output_path.write_bytes(b'{"frame_index":0}\n')
    storage_io.upload_to_storage(
        output_key,
        output_path,
        content_type="application/jsonl",
    )

    assert input_path == tmp_path.joinpath(input_key)
    assert input_path.read_bytes() == b"video-bytes"
    assert output_path == tmp_path.joinpath("keypoints.jsonl")
    assert needs_upload is True
    assert storage.objects[output_key] == b'{"frame_index":0}\n'
    assert storage.content_types[output_key] == "application/jsonl"
