"""Use case: Finalize analysis."""

from backend.app.application.ports.clock import Clock
from backend.app.application.ports.job_repo import JobRepo
from backend.app.domain.analysis_job import AnalysisJob


class FinalizeAnalysis:
    """Use case for finalizing completed analysis."""

    def __init__(self, job_repo: JobRepo, clock: Clock) -> None:
        """
        Initialize use case.

        Args:
            job_repo: Job repository
            clock: Clock for timestamps
        """
        self._job_repo = job_repo
        self._clock = clock

    def execute(self, job: AnalysisJob) -> None:
        """
        Finalize analysis (mark as SUCCEEDED).

        Args:
            job: Analysis job to finalize (already loaded and locked)

        Raises:
            ValueError: If not all stages are done
        """
        # Finalize job (domain method checks invariants)
        job.finalize()

        # Save job (commit will be handled by UoW)
        self._job_repo.save_job(job)
