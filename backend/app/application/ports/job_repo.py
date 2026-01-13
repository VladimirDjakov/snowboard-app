"""Port for job repository."""

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from backend.app.domain.analysis_job import AnalysisJob

if TYPE_CHECKING:
    from backend.app.domain.value_objects import ArtifactRef


class JobRepo(Protocol):
    """Interface for job repository."""

    def get_job(self, video_id: UUID) -> AnalysisJob | None:
        """
        Get analysis job by video ID.

        Args:
            video_id: Video identifier

        Returns:
            AnalysisJob if found, None otherwise
        """
        ...

    def save_job(self, job: AnalysisJob) -> None:
        """
        Save analysis job.

        Args:
            job: AnalysisJob to save

        Raises:
            ValueError: If optimistic locking conflict (version mismatch)
        """
        ...

    def create_job(self, video_id: UUID) -> AnalysisJob:
        """
        Create a new analysis job.

        Args:
            video_id: Video identifier

        Returns:
            New AnalysisJob with CREATED status
        """
        ...

    def lock_job(self, video_id: UUID) -> AnalysisJob | None:
        """
        Lock and get job for concurrent access (pessimistic locking).

        Args:
            video_id: Video identifier

        Returns:
            AnalysisJob if found, None otherwise
        """
        ...

    def register_artifacts(
        self,
        video_id: UUID,
        artifacts: list["ArtifactRef"],  # noqa: F821
    ) -> None:
        """
        Register artifacts for a video.

        Args:
            video_id: Video identifier
            artifacts: List of artifact references to register
        """
        ...

    def get_artifacts(self, video_id: UUID) -> list["ArtifactRef"] | None:  # noqa: F821
        """
        Get all artifacts for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of ArtifactRef if video found, None otherwise
        """
        ...
