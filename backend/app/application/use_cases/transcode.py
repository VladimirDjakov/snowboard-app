"""Use case for running transcode stage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from backend.app.application.interfaces.storage import Storage
from backend.app.application.interfaces.transcoder import VideoMetadata, VideoTranscoder
from backend.app.application.use_cases.analysis import (
    FailAnalysis,
    HandleStageCompleted,
    HandleStageStarted,
)
from backend.app.domain.analysis_job import Stage
from backend.app.domain.value_objects import Artifact, ArtifactKind

TARGET_FPS = 30
NORMALIZED_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class TranscodeOutcome:
    """Result of a successful transcode stage."""

    artifact: Artifact
    metadata: VideoMetadata


class RunTranscodeStage:
    """Use case that performs transcode and advances pipeline."""

    def __init__(
        self,
        storage: Storage,
        transcoder: VideoTranscoder,
        handle_stage_started: HandleStageStarted,
        handle_stage_completed: HandleStageCompleted,
        fail_analysis: FailAnalysis,
    ) -> None:
        """
        Initialize use case.

        Args:
            storage: Storage adapter
            transcoder: Video transcoder adapter
            handle_stage_started: Use case for starting stage
            handle_stage_completed: Use case for completing stage
            fail_analysis: Use case for failing stage
        """
        self._storage = storage
        self._transcoder = transcoder
        self._handle_stage_started = handle_stage_started
        self._handle_stage_completed = handle_stage_completed
        self._fail_analysis = fail_analysis

    def execute(self, video_id: UUID) -> TranscodeOutcome | None:
        """
        Run transcode stage for a video.

        Returns:
            TranscodeOutcome when work is performed, None when already completed.
        """
        normalized_artifact = Artifact(
            kind=ArtifactKind.NORMALIZED,
            version=NORMALIZED_VERSION,
            storage_path=f"proc/{video_id}/normalized.mp4",
        )
        original_storage_path = f"raw/{video_id}/original.mp4"
        normalized_storage_path = normalized_artifact.storage_path

        if self._storage.exists(normalized_storage_path):
            self._handle_stage_completed.execute(video_id, Stage.TRANSCODE, [normalized_artifact])
            return None

        self._handle_stage_started.execute(video_id, Stage.TRANSCODE)

        try:
            with TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                input_path = _materialize_from_storage(
                    self._storage,
                    original_storage_path,
                    base_dir=base_dir,
                )
                output_path, needs_upload = _prepare_output_path(
                    self._storage, normalized_storage_path, base_dir=base_dir
                )
                self._transcoder.normalize(input_path, output_path, fps=TARGET_FPS)
                metadata = self._transcoder.probe(output_path)

                if needs_upload:
                    _upload_to_storage(
                        self._storage,
                        normalized_storage_path,
                        output_path,
                        content_type="video/mp4",
                    )

            self._handle_stage_completed.execute(
                video_id,
                Stage.TRANSCODE,
                [normalized_artifact],
            )
            return TranscodeOutcome(artifact=normalized_artifact, metadata=metadata)
        except Exception as exc:
            self._fail_analysis.execute(video_id, Stage.TRANSCODE, str(exc))
            raise


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _materialize_from_storage(storage: Storage, storage_path: str, *, base_dir: Path) -> Path:
    local_path = storage.get_file_path(storage_path)
    if local_path is not None and local_path.exists():
        return local_path

    target_path = base_dir / storage_path
    _ensure_parent_dir(target_path)
    target_path.write_bytes(storage.read_file(storage_path))
    return target_path


def _prepare_output_path(
    storage: Storage, storage_path: str, *, base_dir: Path
) -> tuple[Path, bool]:
    local_path = storage.get_file_path(storage_path)
    if local_path is None:
        return base_dir / "normalized.mp4", True
    _ensure_parent_dir(local_path)
    return local_path, False


def _upload_to_storage(
    storage: Storage,
    storage_path: str,
    file_path: Path,
    *,
    content_type: str | None = None,
) -> None:
    storage.write_file(storage_path, file_path.read_bytes(), content_type=content_type)
