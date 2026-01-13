"""PostgreSQL adapter for JobRepo."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.application.ports.job_repo import JobRepo
from backend.app.domain.analysis_job import (
    AnalysisJob,
    AnalysisJobStatus,
    Stage,
    StageStatus,
)
from backend.app.domain.value_objects import ArtifactRef

# NOTE: This import style is a compromise.
# See: docs/clean_architecture.md (section "Dependency Rule и размещение ORM моделей")
from backend.app.infrastructure.postgres.orm_models import (
    Artifact,
    JobStage,
    Video,
    VideoStatus,
)


class PostgresJobRepo(JobRepo):
    """PostgreSQL implementation of JobRepo."""

    def __init__(self, session: Session) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self._session = session

    def get_job(self, video_id: UUID) -> AnalysisJob | None:
        """Get analysis job by video ID."""
        video = self._session.get(Video, video_id)
        if video is None:
            return None

        return self._to_domain(video)

    def save_job(self, job: AnalysisJob) -> None:
        """Save analysis job with optimistic locking."""
        video = self._session.get(Video, job.video_id)
        if video is None:
            raise ValueError(f"Video {job.video_id} not found")

        # Optimistic locking: check version
        if video.version != job.version:
            raise ValueError(
                f"Optimistic locking conflict: expected version {job.version}, "
                f"but database has version {video.version}"
            )

        # Map domain status to ORM status
        video.status = self._map_job_status_to_video_status(job.status)
        # Increment version for optimistic locking
        video.version = job.version + 1

        # Update or create stages
        for stage, stage_status in job.stages.items():
            # Find existing stage or create new
            stmt = select(JobStage).where(
                JobStage.video_id == job.video_id,
                JobStage.name == stage,
            )
            existing_stage = self._session.scalar(stmt)

            if existing_stage:
                existing_stage.status = stage_status
            else:
                new_stage = JobStage(
                    video_id=job.video_id,
                    name=stage,
                    status=stage_status,
                )
                self._session.add(new_stage)

        # Save error message if present
        if job.error_message:
            # Store in the first failed stage or create a placeholder
            failed_stages = [s for s, status in job.stages.items() if status == StageStatus.FAILED]
            if failed_stages:
                stmt = select(JobStage).where(
                    JobStage.video_id == job.video_id,
                    JobStage.name == failed_stages[0],
                )
                stage_obj = self._session.scalar(stmt)
                if stage_obj:
                    stage_obj.error_message = job.error_message

        # Note: commit() is now handled by UoW, not here

    def register_artifacts(
        self,
        video_id: UUID,
        artifacts: list[ArtifactRef],
    ) -> None:
        """
        Register artifacts for a video.

        Args:
            video_id: Video identifier
            artifacts: List of artifact references to register
        """

        for artifact_ref in artifacts:
            # Check if artifact already exists
            stmt = select(Artifact).where(
                Artifact.video_id == video_id,
                Artifact.kind == artifact_ref.kind,
                Artifact.version == artifact_ref.version,
            )
            existing = self._session.scalar(stmt)

            if not existing:
                new_artifact = Artifact(
                    video_id=video_id,
                    kind=artifact_ref.kind,
                    version=artifact_ref.version,
                    object_key=artifact_ref.object_key,
                )
                self._session.add(new_artifact)

        # Note: commit() is now handled by UoW, not here

    def create_job(self, video_id: UUID) -> AnalysisJob:
        """Create a new analysis job."""
        video = self._session.get(Video, video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")

        # Create job with CREATED status
        job = AnalysisJob(
            video_id=video_id,
            status=AnalysisJobStatus.CREATED,
        )

        # Initialize all stages as PENDING
        for stage in Stage:
            job.stages[stage] = StageStatus.PENDING

        # Save to database
        self.save_job(job)

        return job

    def lock_job(self, video_id: UUID) -> AnalysisJob | None:
        """Lock and get job for concurrent access (pessimistic locking)."""
        stmt = select(Video).where(Video.id == video_id).with_for_update()
        video = self._session.scalar(stmt)
        if video is None:
            return None

        return self._to_domain(video)

    def get_artifacts(self, video_id: UUID) -> list[ArtifactRef] | None:
        """
        Get all artifacts for a video.

        Args:
            video_id: Video identifier

        Returns:
            List of ArtifactRef if video found, None otherwise
        """
        # Check if video exists
        video = self._session.get(Video, video_id)
        if video is None:
            return None

        # Query all artifacts for this video
        stmt = select(Artifact).where(Artifact.video_id == video_id)
        artifacts = self._session.scalars(stmt).all()

        # Map ORM Artifact to domain ArtifactRef
        return [
            ArtifactRef(
                kind=artifact.kind,
                version=artifact.version,
                object_key=artifact.object_key,
            )
            for artifact in artifacts
        ]

    def _to_domain(self, video: Video) -> AnalysisJob:
        """Convert ORM Video to domain AnalysisJob."""
        # Map Video status to AnalysisJob status
        job_status = self._map_video_status_to_job_status(video.status)

        # Build stages dict from JobStage records
        stages: dict[Stage, StageStatus] = {}
        for orm_stage in video.stages:
            stages[orm_stage.name] = orm_stage.status

        # Initialize missing stages as PENDING
        for stage in Stage:
            if stage not in stages:
                stages[stage] = StageStatus.PENDING

        # Get error message from first failed stage
        error_message = None
        for orm_stage in video.stages:
            if orm_stage.status == StageStatus.FAILED and orm_stage.error_message:
                error_message = orm_stage.error_message
                break

        return AnalysisJob(
            video_id=video.id,
            status=job_status,
            stages=stages,
            version=video.version,
            error_message=error_message,
        )

    @staticmethod
    def _map_video_status_to_job_status(video_status: VideoStatus) -> AnalysisJobStatus:
        """Map VideoStatus to AnalysisJobStatus."""
        mapping = {
            VideoStatus.CREATED: AnalysisJobStatus.CREATED,
            VideoStatus.UPLOADED: AnalysisJobStatus.CREATED,  # Upload is separate lifecycle
            VideoStatus.PROCESSING: AnalysisJobStatus.RUNNING,
            VideoStatus.DONE: AnalysisJobStatus.SUCCEEDED,
            VideoStatus.FAILED: AnalysisJobStatus.FAILED,
            VideoStatus.CANCELED: AnalysisJobStatus.CANCELED,
        }
        return mapping.get(video_status, AnalysisJobStatus.CREATED)

    @staticmethod
    def _map_job_status_to_video_status(job_status: AnalysisJobStatus) -> VideoStatus:
        """Map AnalysisJobStatus to VideoStatus."""
        mapping = {
            AnalysisJobStatus.CREATED: VideoStatus.CREATED,
            AnalysisJobStatus.QUEUED: VideoStatus.PROCESSING,
            AnalysisJobStatus.RUNNING: VideoStatus.PROCESSING,
            AnalysisJobStatus.SUCCEEDED: VideoStatus.DONE,
            AnalysisJobStatus.FAILED: VideoStatus.FAILED,
            AnalysisJobStatus.CANCELED: VideoStatus.CANCELED,
        }
        return mapping.get(job_status, VideoStatus.CREATED)
