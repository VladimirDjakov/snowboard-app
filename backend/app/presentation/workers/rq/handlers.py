"""RQ task entrypoints for worker stages."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.workers.features import FeaturesWorker
from backend.app.presentation.workers.feedback import FeedbackWorker
from backend.app.presentation.workers.normalize import NormalizeWorker
from backend.app.presentation.workers.pose import PoseWorker

logger = logging.getLogger(__name__)


def normalize_task(video_id: str) -> None:
    """RQ task entrypoint for normalize stage."""
    video_uuid = UUID(video_id)
    logger.info("Normalize task started", extra={"video_id": str(video_uuid)})
    NormalizeWorker().run_stage(Stage.NORMALIZE, video_uuid)
    logger.info("Normalize task completed", extra={"video_id": str(video_uuid)})


def pose_task(video_id: str) -> None:
    """RQ task entrypoint for pose stage."""
    video_uuid = UUID(video_id)
    logger.info("Pose task started", extra={"video_id": str(video_uuid)})
    PoseWorker().run_stage(Stage.POSE, video_uuid)
    logger.info("Pose task completed", extra={"video_id": str(video_uuid)})


def features_task(video_id: str) -> None:
    """RQ task entrypoint for features stage."""
    video_uuid = UUID(video_id)
    logger.info("Features task started", extra={"video_id": str(video_uuid)})
    FeaturesWorker().run_stage(Stage.FEATURES, video_uuid)
    logger.info("Features task completed", extra={"video_id": str(video_uuid)})


def feedback_task(video_id: str) -> None:
    """RQ task entrypoint for feedback stage."""
    video_uuid = UUID(video_id)
    logger.info("Feedback task started", extra={"video_id": str(video_uuid)})
    FeedbackWorker().run_stage(Stage.FEEDBACK, video_uuid)
    logger.info("Feedback task completed", extra={"video_id": str(video_uuid)})
