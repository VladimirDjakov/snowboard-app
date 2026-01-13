"""Video I/O helpers for workers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.infrastructure.storage.base import BaseStorage


@dataclass
class VideoMetadata:
    """Video metadata extracted from ffprobe."""

    width: int | None
    height: int | None
    duration_sec: float | None
    fps: float | None
    nb_frames: float | None


def ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory exists for a file path."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
    )


def run_ffmpeg(args: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    _run_command(args)


def probe_video(path: Path) -> VideoMetadata:
    """Probe video metadata via ffprobe."""
    result = _run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            path.as_posix(),
        ]
    )
    data = json.loads(result.stdout)
    return _extract_video_metadata(data)


def _extract_video_metadata(ffprobe_json: dict[str, Any]) -> VideoMetadata:
    streams = ffprobe_json.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    width = video_stream.get("width")
    height = video_stream.get("height")
    duration = _parse_number(ffprobe_json.get("format", {}).get("duration"))
    fps = _parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

    return VideoMetadata(
        width=width,
        height=height,
        duration_sec=duration,
        fps=fps,
        nb_frames=_parse_number(video_stream.get("nb_frames")),
    )


def _parse_fraction(value: Any) -> float | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and "/" in value:
        num, den = value.split("/", 1)
        try:
            return float(num) / float(den)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_video(
    input_path: Path | str,
    output_path: Path | str,
    *,
    fps: int = 30,
    width: int | None = None,
    height: int | None = None,
    video_codec: str = "libx264",
    preset: str = "fast",
    crf: int = 23,
    keep_audio: bool = False,
) -> Path:
    """
    Normalize video with ffmpeg.

    Returns the output path.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    ensure_parent_dir(output_path)

    filters: list[str] = []
    if fps:
        filters.append(f"fps={fps}")
    if width is not None and height is not None:
        filters.append(f"scale={width}:{height}")

    args = ["ffmpeg", "-y", "-i", str(input_path)]
    if filters:
        args += ["-vf", ",".join(filters)]
    args += ["-c:v", video_codec, "-preset", preset, "-crf", str(crf)]
    if not keep_audio:
        args.append("-an")
    args.append(str(output_path))

    run_ffmpeg(args)
    return output_path


def materialize_from_storage(
    storage: BaseStorage,
    storage_path: str,
    *,
    base_dir: Path,
) -> Path:
    """
    Ensure a storage object is available as a local file.

    For local storage, returns the existing file path.
    For remote storage, downloads the object into base_dir.
    """
    local_path = storage.get_file_path(storage_path)
    if local_path is not None and local_path.exists():
        return local_path

    target_path = base_dir / storage_path
    ensure_parent_dir(target_path)
    target_path.write_bytes(storage.read_file(storage_path))
    return target_path


def upload_to_storage(
    storage: BaseStorage,
    storage_path: str,
    file_path: Path | str,
    *,
    content_type: str | None = None,
) -> None:
    """Upload a local file to storage."""
    file_path = Path(file_path)
    storage.write_file(storage_path, file_path.read_bytes(), content_type=content_type)
