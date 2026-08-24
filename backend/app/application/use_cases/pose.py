"""Use case for running pose stage (keypoints extraction)."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from backend.app.application.interfaces.job_repo import JobRepo
from backend.app.application.interfaces.pose_estimator import PoseEstimator, PoseVideo
from backend.app.application.interfaces.storage import Storage
from backend.app.application.interfaces.storage_io import StorageIO
from backend.app.application.use_cases.analysis import (
    FailAnalysis,
    HandleStageCompleted,
    HandleStageStarted,
)
from backend.app.domain.analysis_job import Stage
from backend.app.domain.value_objects import Artifact, ArtifactKind

KEYPOINTS_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class PoseResult:
    """Result of a successful pose stage."""

    artifact: Artifact
    fps: float | None
    nb_frames: int
    target_track_id: int | None


class RunPoseStage:
    """Use case that extracts keypoints and advances pipeline."""

    def __init__(
        self,
        storage: Storage,
        storage_io: StorageIO,
        job_repo: JobRepo,
        pose_estimator: PoseEstimator,
        handle_stage_started: HandleStageStarted,
        handle_stage_completed: HandleStageCompleted,
        fail_analysis: FailAnalysis,
    ) -> None:
        self._storage = storage
        self._storage_io = storage_io
        self._job_repo = job_repo
        self._pose_estimator = pose_estimator
        self._handle_stage_started = handle_stage_started
        self._handle_stage_completed = handle_stage_completed
        self._fail_analysis = fail_analysis

    def execute(self, video_id: UUID) -> PoseResult | None:
        """
        Run pose stage for a video.

        Returns:
            PoseResult when work is performed, None when already completed.
        """
        keypoints_artifact = Artifact(
            kind=ArtifactKind.KEYPOINTS,
            version=KEYPOINTS_VERSION,
            storage_path=f"proc/{video_id}/keypoints_{KEYPOINTS_VERSION}.jsonl",
        )
        self._handle_stage_started.execute(video_id, Stage.POSE)

        if self._storage.exists(keypoints_artifact.storage_path):
            self._handle_stage_completed.execute(video_id, Stage.POSE, [keypoints_artifact])
            return None

        try:
            normalized_artifact = self._resolve_normalized_artifact(video_id)

            with TemporaryDirectory() as tmp_dir:
                base_dir = Path(tmp_dir)
                video_path = self._storage_io.materialize_from_storage(
                    normalized_artifact.storage_path,
                    base_dir=base_dir,
                )
                output_path, needs_upload = self._storage_io.prepare_output_path(
                    keypoints_artifact.storage_path,
                    base_dir=base_dir,
                    default_filename="keypoints.jsonl",
                )

                pose_video = self._pose_estimator.estimate(video_path)
                target_track_id = _select_target_track_id(pose_video)
                _write_keypoints_jsonl(pose_video, output_path, target_track_id=target_track_id)

                if needs_upload:
                    self._storage_io.upload_to_storage(
                        keypoints_artifact.storage_path,
                        output_path,
                        content_type="application/jsonl",
                    )

            self._handle_stage_completed.execute(
                video_id,
                Stage.POSE,
                [keypoints_artifact],
            )
            return PoseResult(
                artifact=keypoints_artifact,
                fps=pose_video.fps,
                nb_frames=len(pose_video.frames),
                target_track_id=target_track_id,
            )
        except Exception as exc:
            self._fail_analysis.execute(video_id, Stage.POSE, str(exc))
            raise

    def _resolve_normalized_artifact(self, video_id: UUID) -> Artifact:
        artifacts = self._job_repo.get_artifacts(video_id) or []
        normalized = next((a for a in artifacts if a.kind == ArtifactKind.NORMALIZED), None)
        if normalized is None:
            raise ValueError(f"Normalized artifact not found for video {video_id}")
        return normalized


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _select_target_track_id(pose_video: PoseVideo) -> int | None:
    presence_counts: dict[int, int] = defaultdict(int)
    for frame in pose_video.frames:
        for det in frame.detections:
            if det.track_id is None:
                continue
            presence_counts[det.track_id] += 1
    if not presence_counts:
        return None
    return max(presence_counts, key=presence_counts.get)


def _write_keypoints_jsonl(
    pose_video: PoseVideo,
    output_path: Path,
    *,
    target_track_id: int | None,
) -> None:
    _ensure_parent_dir(output_path)
    fps = pose_video.fps
    names = pose_video.keypoint_names

    with output_path.open("w", encoding="utf-8") as f:
        for frame in pose_video.frames:
            det = _select_detection(frame.detections, target_track_id=target_track_id)
            record = {
                "version": KEYPOINTS_VERSION,
                "frame_index": frame.frame_index,
                "timestamp_sec": (frame.frame_index / fps) if fps else None,
                "track_id": det.track_id if det else None,
                "keypoints": _serialize_keypoints(det, names) if det else None,
            }
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")


def _select_detection(detections, *, target_track_id: int | None):
    if not detections:
        return None
    if target_track_id is None:
        return max(detections, key=_detection_score)
    for det in detections:
        if det.track_id == target_track_id:
            return det
    return None


def _detection_score(det) -> float:
    """Average confidence score of a detection."""
    conf = getattr(det, "conf", None) or []
    if not conf:
        return 0.0
    vals = [c for c in conf if isinstance(c, (int, float)) and math.isfinite(float(c))]
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _serialize_keypoints(det, names: list[str]) -> dict[str, object]:
    xy = getattr(det, "xy", None) or []
    conf = getattr(det, "conf", None) or []
    if len(xy) != len(names):
        # Best-effort: keep alignment by truncating to the shortest length.
        n = min(len(xy), len(names))
        xy = xy[:n]
        names = names[:n]
        conf = conf[:n]
    if len(conf) != len(names):
        n = min(len(conf), len(names))
        xy = xy[:n]
        names = names[:n]
        conf = conf[:n]

    return {
        "names": names,
        "xy": [[_finite_or_none(p[0]), _finite_or_none(p[1])] for p in xy],
        "conf": [_finite_or_none(c) for c in conf],
    }


def _finite_or_none(value) -> float | None:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(val):
        return val
    return None
