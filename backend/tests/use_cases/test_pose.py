"""Unit tests for pose stage use case."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.application.interfaces.pose_estimator import (
    PoseDetection,
    PoseFrame,
    PoseVideo,
    XYPoint,
)
from backend.app.application.use_cases.pose import KEYPOINTS_VERSION, RunPoseStage
from backend.app.domain.analysis_job import Stage
from backend.app.domain.value_objects import Artifact, ArtifactKind
from backend.app.infrastructure.storage.local import LocalStorage
from backend.app.infrastructure.storage.storage_io import DefaultStorageIO


class StubPoseEstimator:
    def __init__(self, pose_video: PoseVideo) -> None:
        self.pose_video = pose_video
        self.calls: list[Path] = []

    def estimate(self, video_path: Path) -> PoseVideo:
        self.calls.append(video_path)
        return self.pose_video


def test_pose_stage_writes_keypoints_jsonl_and_completes(tmp_path: Path) -> None:
    video_id = uuid4()
    storage = LocalStorage(tmp_path.joinpath("storage"))
    storage_io = DefaultStorageIO(storage)

    normalized_artifact = Artifact(
        kind=ArtifactKind.NORMALIZED,
        version="v1",
        storage_path=f"proc/{video_id}/normalized.mp4",
    )
    normalized_path = storage.get_file_path(normalized_artifact.storage_path)
    assert normalized_path is not None
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_bytes(b"not-a-real-video-but-ok-for-tests")

    pose_video = PoseVideo(
        fps=25.0,
        keypoint_names=["nose", "left_eye"],
        frames=[
            PoseFrame(
                frame_index=0,
                detections=[
                    PoseDetection(
                        track_id=10,
                        xy=[XYPoint(1.0, 2.0), XYPoint(3.0, 4.0)],
                        conf=[0.9, 0.8],
                    ),
                    PoseDetection(
                        track_id=20,
                        xy=[XYPoint(5.0, 6.0), XYPoint(7.0, 8.0)],
                        conf=[0.7, 0.6],
                    ),
                ],
            ),
            PoseFrame(
                frame_index=1,
                detections=[
                    PoseDetection(
                        track_id=10,
                        xy=[XYPoint(9.0, 10.0), XYPoint(11.0, 12.0)],
                        conf=[0.5, 0.4],
                    ),
                ],
            ),
        ],
    )
    estimator = StubPoseEstimator(pose_video)

    job_repo = MagicMock()
    job_repo.get_artifacts.return_value = [normalized_artifact]
    handle_stage_started = MagicMock()
    handle_stage_completed = MagicMock()
    fail_analysis = MagicMock()

    use_case = RunPoseStage(
        storage,
        storage_io,
        job_repo,
        estimator,
        handle_stage_started,
        handle_stage_completed,
        fail_analysis,
    )
    result = use_case.execute(video_id)

    assert result is not None
    assert result.artifact.kind == ArtifactKind.KEYPOINTS
    assert result.artifact.version == KEYPOINTS_VERSION
    assert result.artifact.storage_path.endswith(f"/keypoints_{KEYPOINTS_VERSION}.jsonl")
    assert result.nb_frames == 2
    assert result.target_track_id == 10

    handle_stage_started.execute.assert_called_once_with(video_id, Stage.POSE)
    handle_stage_completed.execute.assert_called_once()
    fail_analysis.execute.assert_not_called()
    assert estimator.calls  # called at least once

    keypoints_path = storage.get_file_path(result.artifact.storage_path)
    assert keypoints_path is not None
    assert keypoints_path.exists()

    lines = keypoints_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rec0 = json.loads(lines[0])
    assert rec0["version"] == KEYPOINTS_VERSION
    assert rec0["frame_index"] == 0
    assert rec0["timestamp_sec"] == 0.0
    assert rec0["track_id"] == 10
    assert rec0["keypoints"]["names"] == ["nose", "left_eye"]


def test_pose_stage_idempotent_when_keypoints_exist(tmp_path: Path) -> None:
    video_id = uuid4()
    storage = LocalStorage(tmp_path.joinpath("storage"))
    storage_io = DefaultStorageIO(storage)

    normalized_artifact = Artifact(
        kind=ArtifactKind.NORMALIZED,
        version="v1",
        storage_path=f"proc/{video_id}/normalized.mp4",
    )
    job_repo = MagicMock()
    job_repo.get_artifacts.return_value = [normalized_artifact]

    # Pre-create keypoints output.
    out_path = storage.get_file_path(f"proc/{video_id}/keypoints_{KEYPOINTS_VERSION}.jsonl")
    assert out_path is not None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('{"version":"v1"}\n', encoding="utf-8")

    estimator = StubPoseEstimator(
        PoseVideo(fps=None, keypoint_names=[], frames=[]),
    )
    handle_stage_started = MagicMock()
    handle_stage_completed = MagicMock()
    fail_analysis = MagicMock()

    use_case = RunPoseStage(
        storage,
        storage_io,
        job_repo,
        estimator,
        handle_stage_started,
        handle_stage_completed,
        fail_analysis,
    )
    result = use_case.execute(video_id)

    assert result is None
    handle_stage_started.execute.assert_called_once_with(video_id, Stage.POSE)
    handle_stage_completed.execute.assert_called_once()
    assert estimator.calls == []
    fail_analysis.execute.assert_not_called()


def test_pose_stage_fails_when_normalized_artifact_is_missing(tmp_path: Path) -> None:
    video_id = uuid4()
    storage = LocalStorage(tmp_path.joinpath("storage"))
    estimator = StubPoseEstimator(PoseVideo(fps=None, keypoint_names=[], frames=[]))
    job_repo = MagicMock()
    job_repo.get_artifacts.return_value = []
    handle_stage_started = MagicMock()
    handle_stage_completed = MagicMock()
    fail_analysis = MagicMock()

    use_case = RunPoseStage(
        storage,
        DefaultStorageIO(storage),
        job_repo,
        estimator,
        handle_stage_started,
        handle_stage_completed,
        fail_analysis,
    )

    with pytest.raises(ValueError, match="Normalized artifact not found"):
        use_case.execute(video_id)

    assert estimator.calls == []
    handle_stage_completed.execute.assert_not_called()
    fail_analysis.execute.assert_called_once()
