"""GPU worker orchestration for processing stages."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import UseCases
from backend.app.presentation.workers.common.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class GPUWorker(BaseWorker):
    """Run GPU-bound stages with shared wiring and lifecycle."""

    @property
    def _logger(self):
        return logger

    def _execute_stage(self, stage: Stage, video_id: UUID, use_cases: UseCases) -> None:
        if stage != Stage.POSE:
            raise ValueError(f"Unsupported stage: {stage}")

        logger.info("Pose task completed (placeholder)", extra={"video_id": str(video_id)})
