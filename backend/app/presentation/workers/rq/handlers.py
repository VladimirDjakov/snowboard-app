"""RQ task entrypoints for worker stages."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.workers.cpu.worker import CPUWorker
from backend.app.presentation.workers.gpu.worker import GPUWorker

logger = logging.getLogger(__name__)


def transcode_task(video_id: str) -> None:
    """RQ task entrypoint for transcode stage."""
    video_uuid = UUID(video_id)
    logger.info("Transcode task started", extra={"video_id": str(video_uuid)})
    CPUWorker().run_stage(Stage.TRANSCODE, video_uuid)
    logger.info("Transcode task completed", extra={"video_id": str(video_uuid)})


def pose_task(video_id: str) -> None:
    """RQ task entrypoint for pose stage."""
    video_uuid = UUID(video_id)
    logger.info("Pose task started", extra={"video_id": str(video_uuid)})
    GPUWorker().run_stage(Stage.POSE, video_uuid)
    logger.info("Pose task completed", extra={"video_id": str(video_uuid)})


def features_task(video_id: str) -> None:
    """RQ task entrypoint for features stage."""
    video_uuid = UUID(video_id)
    logger.info("Features task started", extra={"video_id": str(video_uuid)})
    CPUWorker().run_stage(Stage.FEATURES, video_uuid)
    logger.info("Features task completed", extra={"video_id": str(video_uuid)})


def feedback_task(video_id: str) -> None:
    """RQ task entrypoint for feedback stage."""
    video_uuid = UUID(video_id)
    logger.info("Feedback task started", extra={"video_id": str(video_uuid)})
    CPUWorker().run_stage(Stage.FEEDBACK, video_uuid)
    logger.info("Feedback task completed", extra={"video_id": str(video_uuid)})
