"""Interface for pose estimation (keypoints extraction)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Protocol


class XYPoint(NamedTuple):
    """2D keypoint in source-frame pixel coordinates."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class PoseDetection:
    """Pose for a single detected person in a frame."""

    track_id: int | None
    # Each element is named tuple (x, y) in source-frame coordinates.
    xy: list[XYPoint]
    # Per-keypoint confidence score in [0, 1].
    conf: list[float]


@dataclass(frozen=True, slots=True)
class PoseFrame:
    """All pose detections for a single frame."""

    frame_index: int
    detections: list[PoseDetection]


@dataclass(frozen=True, slots=True)
class PoseVideo:
    """Pose detections for a whole video."""

    fps: float | None
    keypoint_names: list[str]
    frames: list[PoseFrame]


class PoseEstimator(Protocol):
    """Port for pose estimation implementations."""

    def estimate(self, video_path: Path) -> PoseVideo:
        """Run pose estimation on a video file."""
