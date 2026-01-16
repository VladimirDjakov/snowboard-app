"""Interface for video transcoding and probing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Metadata extracted from a video file."""

    width: int | None
    height: int | None
    duration_sec: float | None
    fps: float | None
    nb_frames: float | None


class VideoTranscoder(Protocol):
    """Protocol for video transcoding and probing."""

    def normalize(
        self,
        input_path: Path,
        output_path: Path,
        *,
        fps: int,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Normalize video to a standard format."""
        ...

    def probe(self, path: Path) -> VideoMetadata:
        """Extract metadata from a video file."""
        ...
