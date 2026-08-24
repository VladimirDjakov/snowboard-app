"""Pose worker for GPU-bound stage."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import UseCases
from backend.app.presentation.workers.common.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PoseWorker(BaseWorker):
    """Run the pose stage on GPU."""

    @property
    def _logger(self) -> logging.Logger:
        return logger

    def _execute_stage(self, stage: Stage, video_id: UUID, use_cases: UseCases) -> None:
        logger.info("Pose task completed (placeholder)", extra={"video_id": str(video_id)})
