"""Use case: Get analysis status."""

from uuid import UUID

from backend.app.application.ports.job_repo import JobRepo
from backend.app.domain.analysis_job import AnalysisJob


class GetAnalysisStatus:
    """Use case for getting analysis job status (read-only)."""

    def __init__(self, job_repo: JobRepo) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
        """
        self._job_repo = job_repo

    def execute(self, video_id: UUID) -> AnalysisJob | None:
        """
        Get analysis job status.

        Args:
            video_id: Video identifier

        Returns:
            AnalysisJob if found, None otherwise
        """
        return self._job_repo.get_job(video_id)
