"""Use case: List artifacts."""

from uuid import UUID

from backend.app.application.ports.job_repo import JobRepo
from backend.app.domain.value_objects import ArtifactRef


class ListArtifacts:
    """Use case for listing artifacts for a video (read-only)."""

    def __init__(self, job_repo: JobRepo) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
        """
        self._job_repo = job_repo

    def execute(self, video_id: UUID) -> list[ArtifactRef] | None:
        """
        Get list of artifacts for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of ArtifactRef if video found, None otherwise
        """
        return self._job_repo.get_artifacts(video_id)
