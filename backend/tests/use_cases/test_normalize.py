"""Regression tests for the normalize stage."""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from backend.app.application.interfaces.normalizer import VideoMetadata
from backend.app.application.use_cases.normalize import RunNormalizeStage
from backend.app.domain.analysis_job import Stage
from backend.app.infrastructure.storage.local import LocalStorage
from backend.app.infrastructure.storage.storage_io import DefaultStorageIO


class CopyingNormalizerStub:
    """Normalizer stub that exercises real input and output paths."""

    def normalize(
        self,
        input_path: Path,
        output_path: Path,
        *,
        fps: int,
        max_dim: int | None = None,
        pad_to_max_dim: bool = False,
    ) -> None:
        assert input_path.read_bytes() == b"raw-video"
        assert fps == 25
        assert max_dim == 1280
        assert pad_to_max_dim is True
        output_path.write_bytes(b"normalized-video")

    def probe(self, path: Path) -> VideoMetadata:
        assert path.read_bytes() == b"normalized-video"
        return VideoMetadata(
            width=1280,
            height=720,
            duration_sec=2.0,
            fps=25.0,
            nb_frames=50,
        )


def test_normalize_stage_uses_storage_io_and_completes(tmp_path: Path) -> None:
    video_id = uuid4()
    storage = LocalStorage(tmp_path.joinpath("storage"))
    original_path = storage.get_file_path(f"raw/{video_id}/original.mp4")
    assert original_path is not None
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(b"raw-video")
    handle_stage_started = MagicMock()
    handle_stage_completed = MagicMock()
    fail_analysis = MagicMock()
    use_case = RunNormalizeStage(
        storage,
        DefaultStorageIO(storage),
        CopyingNormalizerStub(),
        handle_stage_started,
        handle_stage_completed,
        fail_analysis,
        target_fps=25,
        target_max_dim=1280,
        pad_to_max_dim=True,
    )

    result = use_case.execute(video_id)

    assert result is not None
    assert result.metadata.nb_frames == 50
    normalized_path = storage.get_file_path(result.artifact.storage_path)
    assert normalized_path is not None
    assert normalized_path.read_bytes() == b"normalized-video"
    handle_stage_started.execute.assert_called_once_with(video_id, Stage.NORMALIZE)
    handle_stage_completed.execute.assert_called_once()
    fail_analysis.execute.assert_not_called()
