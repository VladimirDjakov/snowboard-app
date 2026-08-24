"""Ultralytics-based pose estimator adapter.

Designed to be import-safe when Ultralytics/Torch/OpenCV are not installed
(they are optional worker dependencies). Imports happen lazily at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.application.interfaces.pose_estimator import (
    PoseDetection,
    PoseEstimator,
    PoseFrame,
    PoseVideo,
    XYPoint,
)

COCO_KEYPOINT_NAMES: list[str] = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


@dataclass(frozen=True, slots=True)
class UltralyticsPoseConfig:
    model_path: str = "yolov8n-pose.pt"
    device: str = "cpu"  # "cpu" | "mps" | "cuda" | "auto"
    imgsz: int = 640
    conf: float = 0.25
    iou: float = 0.7
    persist: bool = True


def _resolve_device(requested: str) -> str:
    requested = (requested or "cpu").strip().lower()
    if requested != "auto":
        return requested
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class UltralyticsPoseEstimator(PoseEstimator):
    """PoseEstimator implemented using Ultralytics YOLO Pose models."""

    def __init__(self, config: UltralyticsPoseConfig | None = None) -> None:
        self._config = config or UltralyticsPoseConfig()

    def estimate(self, video_path: Path) -> PoseVideo:
        try:
            from ultralytics import YOLO  # type: ignore
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Ultralytics is required for the pose stage. "
                "Install backend optional deps 'workers-gpu' to run PoseWorker."
            ) from exc

        fps = _try_get_fps(video_path)
        device = _resolve_device(self._config.device)
        model = YOLO(self._config.model_path)

        frames: list[PoseFrame] = []
        frame_index = 0

        results_iter = model.track(
            source=video_path.as_posix(),
            stream=True,
            persist=self._config.persist,
            imgsz=self._config.imgsz,
            conf=self._config.conf,
            iou=self._config.iou,
            device=device,
            verbose=False,
        )

        for res in results_iter:
            detections: list[PoseDetection] = []

            track_ids: list[int | None] = []
            if (
                getattr(res, "boxes", None) is not None
                and getattr(res.boxes, "id", None) is not None
            ):
                try:
                    track_ids = [int(x) for x in res.boxes.id.int().tolist()]
                except Exception:
                    track_ids = []

            kpts = getattr(res, "keypoints", None)
            if kpts is not None and getattr(kpts, "xy", None) is not None:
                xy = kpts.xy
                conf = getattr(kpts, "conf", None)

                # Shapes: xy -> (n_det, n_kpt, 2), conf -> (n_det, n_kpt)
                n_det = int(xy.shape[0])
                for det_idx in range(n_det):
                    tid = track_ids[det_idx] if det_idx < len(track_ids) else None
                    xy_list = xy[det_idx].detach().cpu().tolist()
                    conf_list = (
                        conf[det_idx].detach().cpu().tolist()
                        if conf is not None
                        else [1.0 for _ in range(len(xy_list))]
                    )
                    detections.append(
                        PoseDetection(
                            track_id=tid,
                            xy=[XYPoint(float(p[0]), float(p[1])) for p in xy_list],
                            conf=[float(c) for c in conf_list],
                        )
                    )

            frames.append(PoseFrame(frame_index=frame_index, detections=detections))
            frame_index += 1

        return PoseVideo(
            fps=fps,
            keypoint_names=COCO_KEYPOINT_NAMES,
            frames=frames,
        )


def _try_get_fps(video_path: Path) -> float | None:
    try:
        import cv2  # type: ignore
    except ModuleNotFoundError:
        return None
    cap = cv2.VideoCapture(video_path.as_posix())
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps and fps > 0:
            return float(fps)
        return None
    finally:
        cap.release()
