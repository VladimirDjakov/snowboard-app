"""Composition root - dependency injection and wiring."""

from collections.abc import Callable

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from backend.app.adapters.clock.system_clock import SystemClock
from backend.app.adapters.postgres.job_repo import PostgresJobRepo
from backend.app.adapters.postgres.uow import PostgresUnitOfWork
from backend.app.adapters.postgres.video_repo import PostgresVideoRepo
from backend.app.adapters.redis.client import RedisClient
from backend.app.adapters.redis.queue import RedisQueue
from backend.app.adapters.redis.queue_client import QueueClient
from backend.app.adapters.storage import create_storage_backend
from backend.app.application.ports.uow import UnitOfWork
from backend.app.application.use_cases.complete_upload import CompleteUpload
from backend.app.application.use_cases.create_video import CreateVideo
from backend.app.application.use_cases.fail_analysis import FailAnalysis
from backend.app.application.use_cases.finalize_analysis import FinalizeAnalysis
from backend.app.application.use_cases.get_status import GetAnalysisStatus
from backend.app.application.use_cases.get_video_artifacts import GetVideoArtifacts
from backend.app.application.use_cases.get_video_status import GetVideoStatus
from backend.app.application.use_cases.handle_stage_completed import HandleStageCompleted
from backend.app.application.use_cases.list_artifacts import ListArtifacts
from backend.app.application.use_cases.start_analysis import StartAnalysis
from backend.app.composition.settings import Settings
from backend.app.infrastructure.postgres.session import (
    create_engine_from_settings,
    create_sessionmaker_from_engine,
)


class Container:
    """Dependency injection container."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize container with settings.

        Args:
            settings: Application settings
        """
        self._settings = settings

        # Create database engine and session factory
        self._engine: Engine = create_engine_from_settings(settings)
        self._session_factory: Callable[[], Session] = create_sessionmaker_from_engine(self._engine)

        # Create Redis client and queue client
        self._redis_client = RedisClient(settings)
        redis_conn = self._redis_client.get_connection()
        self._queue_client = QueueClient(redis_conn)

        # Initialize shared adapters (stateless)
        self.clock = SystemClock()
        self.queue = RedisQueue(self._queue_client)
        # Create storage backend (implements Storage protocol via duck typing)
        self.storage = create_storage_backend(settings)

    def create_uow(self, session: Session) -> UnitOfWork:
        """
        Create Unit of Work for a session.

        Args:
            session: Database session

        Returns:
            Unit of Work instance
        """
        return PostgresUnitOfWork(session)

    def build_use_cases(self, session: Session) -> "UseCases":
        """
        Build use cases for a specific session.

        Args:
            session: Database session

        Returns:
            UseCases instance with all use cases wired
        """
        # Create UoW for this session
        uow = self.create_uow(session)

        # Create repository for this session
        job_repo = PostgresJobRepo(session)
        video_repo = PostgresVideoRepo(session)

        # Create use cases
        finalize_analysis = FinalizeAnalysis(job_repo, self.clock)
        fail_analysis = FailAnalysis(job_repo, self.clock, uow)
        start_analysis = StartAnalysis(job_repo, self.queue, self.clock, uow)
        handle_stage_completed = HandleStageCompleted(
            job_repo,
            self.queue,
            self.clock,
            uow,
        )
        get_analysis_status = GetAnalysisStatus(job_repo)
        list_artifacts = ListArtifacts(job_repo)
        create_video = CreateVideo(video_repo, self.storage, uow)
        complete_upload = CompleteUpload(
            video_repo,
            start_analysis,
            get_analysis_status,
            uow,
        )
        get_video_status = GetVideoStatus(
            video_repo,
            get_analysis_status,
            list_artifacts,
            self.storage,
        )
        get_video_artifacts = GetVideoArtifacts(
            video_repo,
            list_artifacts,
            self.storage,
        )

        return UseCases(
            create_video=create_video,
            complete_upload=complete_upload,
            get_video_status=get_video_status,
            get_video_artifacts=get_video_artifacts,
            start_analysis=start_analysis,
            handle_stage_completed=handle_stage_completed,
            finalize_analysis=finalize_analysis,
            fail_analysis=fail_analysis,
            get_analysis_status=get_analysis_status,
            list_artifacts=list_artifacts,
        )

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            Database session
        """
        return self._session_factory()

    def check_database_health(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()  # Execute and fetch to ensure query runs
            return True
        except Exception:
            return False

    def check_redis_health(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        return self._redis_client.check_health()

    def check_storage_health(self) -> bool:
        """
        Check storage backend health.

        Returns:
            True if storage is healthy, False otherwise
        """
        try:
            # Try to check if storage is accessible by checking a non-existent key
            # This doesn't create anything but verifies storage is working
            self.storage.exists("__health_check__")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close database engine and Redis connection."""
        self._engine.dispose()
        self._redis_client.close()


class UseCases:
    """Container for use cases."""

    def __init__(
        self,
        create_video: CreateVideo,
        complete_upload: CompleteUpload,
        get_video_status: GetVideoStatus,
        get_video_artifacts: GetVideoArtifacts,
        start_analysis: StartAnalysis,
        handle_stage_completed: HandleStageCompleted,
        finalize_analysis: FinalizeAnalysis,
        fail_analysis: FailAnalysis,
        get_analysis_status: GetAnalysisStatus,
        list_artifacts: ListArtifacts,
    ) -> None:
        """Initialize use cases container."""
        self.create_video = create_video
        self.complete_upload = complete_upload
        self.get_video_status = get_video_status
        self.get_video_artifacts = get_video_artifacts
        self.start_analysis = start_analysis
        self.handle_stage_completed = handle_stage_completed
        self.finalize_analysis = finalize_analysis
        self.fail_analysis = fail_analysis
        self.get_analysis_status = get_analysis_status
        self.list_artifacts = list_artifacts
