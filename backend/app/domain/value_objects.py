"""Value objects for domain layer."""

from dataclasses import dataclass
from enum import Enum


class ArtifactKind(str, Enum):
    """Artifact kinds in the system."""

    ORIGINAL = "original_video"
    NORMALIZED = "normalized_video"
    KEYPOINTS = "keypoints"
    FEATURES = "features"
    FEEDBACK = "feedback"


@dataclass(frozen=True)
class Artifact:
    """Artifact of a video analysis."""

    kind: ArtifactKind
    version: str
    storage_path: str


class VideoStatus(str, Enum):
    """Status for a video record."""

    CREATED = "created"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"
