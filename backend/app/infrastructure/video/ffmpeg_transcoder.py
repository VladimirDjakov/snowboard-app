"""FFmpeg-based implementation of VideoTranscoder."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.application.interfaces.transcoder import VideoMetadata, VideoTranscoder


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
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


@dataclass(frozen=True, slots=True)
class FfmpegTranscoder(VideoTranscoder):
    """FFmpeg-backed transcoder implementation."""

    video_codec: str = "libx264"
    preset: str = "fast"
    crf: int = 23
    keep_audio: bool = False

    def normalize(
        self,
        input_path: Path,
        output_path: Path,
        *,
        fps: int,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        filters: list[str] = []
        if fps:
            filters.append(f"fps={fps}")
        if width is not None and height is not None:
            filters.append(f"scale={width}:{height}")

        args = ["ffmpeg", "-y", "-i", str(input_path)]
        if filters:
            args += ["-vf", ",".join(filters)]
        args += ["-c:v", self.video_codec, "-preset", self.preset, "-crf", str(self.crf)]
        if not self.keep_audio:
            args.append("-an")
        args.append(str(output_path))

        _run_command(args)

    def probe(self, path: Path) -> VideoMetadata:
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
