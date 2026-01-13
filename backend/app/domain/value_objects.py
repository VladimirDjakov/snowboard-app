"""Value objects for domain layer."""

from dataclasses import dataclass
from enum import Enum


class ArtifactKind(str, Enum):
    """Artifact kinds in the system."""

    ORIGINAL = "original"
    NORMALIZED = "normalized"
    KEYPOINTS = "keypoints"
    FEATURES = "features"
    FEEDBACK = "feedback"


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to an artifact stored in artifact store."""

    kind: ArtifactKind
    version: str
    object_key: str
