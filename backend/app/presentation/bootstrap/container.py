"""Composition root - dependency injection and wiring."""

from collections.abc import Callable

from redis import Redis
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from backend.app.application.interfaces.uow import UnitOfWork
from backend.app.application.use_cases.analysis import (
    FailAnalysis,
    FinalizeAnalysis,
    GetAnalysisStatus,
    HandleStageCompleted,
    HandleStageStarted,
    ListArtifacts,
    StartAnalysis,
)
from backend.app.application.use_cases.normalize import RunNormalizeStage
from backend.app.application.use_cases.pose import RunPoseStage
from backend.app.application.use_cases.video import (
    CompleteUpload,
    CreateVideo,
    GetVideoArtifacts,
    GetVideoStatus,
)
from backend.app.infrastructure.clock.system_clock import SystemClock
from backend.app.infrastructure.db.job_repo import PostgresJobRepo
from backend.app.infrastructure.db.session import (
    create_engine_from_settings,
    create_session_factory,
)
from backend.app.infrastructure.db.uow import PostgresUnitOfWork
from backend.app.infrastructure.db.video_repo import PostgresVideoRepo
from backend.app.infrastructure.pose.ultralytics_pose_estimator import (
    UltralyticsPoseConfig,
    UltralyticsPoseEstimator,
)
from backend.app.infrastructure.queue.redis_client import RedisClient
from backend.app.infrastructure.queue.redis_queue import RedisQueue
from backend.app.infrastructure.storage import create_storage_backend
from backend.app.infrastructure.storage.storage_io import DefaultStorageIO
from backend.app.infrastructure.video.ffmpeg_normalizer import FfmpegNormalizer
from backend.app.presentation.bootstrap.settings import Settings
from backend.app.presentation.workers.common.contracts import load_contract
from backend.app.presentation.workers.rq.task_registry import TASK_MAP


class Container:
    """Dependency injection container."""

    # TODO: create dependencies for api and workers in separate methods
    # TODO: implement lazy connections for db and queue

    def __init__(self, settings: Settings) -> None:
        """
        Initialize container with settings.

        Args:
            settings: Application settings
        """
        self._settings = settings
        # Create database engine and session factory
        self._engine: Engine = create_engine_from_settings(settings)
        self._session_factory: Callable[[], Session] = create_session_factory(self._engine)

        # Create Redis client
        self._redis_client = RedisClient(settings)
        redis_conn = self._redis_client.get_connection()
        # Initialize shared adapters (stateless)
        self.clock = SystemClock()
        self._queue = RedisQueue(redis_conn, TASK_MAP)
        # Create storage backend (implements Storage protocol via duck typing)
        self.storage = create_storage_backend(settings)
        self.storage_io = DefaultStorageIO(self.storage)
        self.normalizer = FfmpegNormalizer()
        self._normalize_targets = self._resolve_normalize_targets()

    def _resolve_normalize_targets(self) -> dict[str, int]:
        contract = load_contract()
        input_spec = contract.get("input", {}) if isinstance(contract, dict) else {}
        fps = input_spec.get("fps")
        max_dim = input_spec.get("max_dim")
        pad_to_max_dim = input_spec.get("pad_to_max_dim")

        target_fps = fps or 30
        target_max_dim = max_dim
        target_pad_to_max_dim = pad_to_max_dim

        return {
            "fps": int(target_fps) if target_fps is not None else 30,
            "max_dim": int(target_max_dim) if target_max_dim is not None else None,
            "pad_to_max_dim": bool(target_pad_to_max_dim)
            if target_pad_to_max_dim is not None
            else False,
        }

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
        start_analysis = StartAnalysis(job_repo, self._queue, self.clock, uow)
        handle_stage_completed = HandleStageCompleted(
            job_repo,
            self._queue,
            self.clock,
            uow,
        )
        handle_stage_started = HandleStageStarted(job_repo, uow)
        pose_estimator = UltralyticsPoseEstimator(
            UltralyticsPoseConfig(
                model_path=self.settings.pose_model_path,
                device=self.settings.pose_device,
                imgsz=self.settings.pose_imgsz,
                conf=self.settings.pose_conf,
                iou=self.settings.pose_iou,
            )
        )
        normalize_stage = RunNormalizeStage(
            self.storage,
            self.storage_io,
            self.normalizer,
            handle_stage_started,
            handle_stage_completed,
            fail_analysis,
            target_fps=self._normalize_targets["fps"],
            target_max_dim=self._normalize_targets["max_dim"],
            pad_to_max_dim=self._normalize_targets["pad_to_max_dim"],
        )
        pose_stage = RunPoseStage(
            self.storage,
            self.storage_io,
            job_repo,
            pose_estimator,
            handle_stage_started,
            handle_stage_completed,
            fail_analysis,
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
            handle_stage_started=handle_stage_started,
            normalize_stage=normalize_stage,
            pose_stage=pose_stage,
            finalize_analysis=finalize_analysis,
            fail_analysis=fail_analysis,
            get_analysis_status=get_analysis_status,
            list_artifacts=list_artifacts,
        )

    def get_db_session(self) -> Session:
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
            with self._session_factory() as session:
                session.execute(text("SELECT 1"))
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

    def get_redis_connection(self) -> Redis:
        """Get Redis connection for infrastructure workers."""
        return self._redis_client.get_connection()

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
        handle_stage_started: HandleStageStarted,
        normalize_stage: RunNormalizeStage,
        pose_stage: RunPoseStage,
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
        self.handle_stage_started = handle_stage_started
        self.normalize_stage = normalize_stage
        self.pose_stage = pose_stage
        self.finalize_analysis = finalize_analysis
        self.fail_analysis = fail_analysis
        self.get_analysis_status = get_analysis_status
        self.list_artifacts = list_artifacts
