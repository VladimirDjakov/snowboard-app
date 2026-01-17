"""Normalize worker for CPU-bound stage."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import UseCases
from backend.app.presentation.workers.common.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class NormalizeWorker(BaseWorker):
    """Run the normalize stage on CPU."""

    @property
    def _logger(self) -> logging.Logger:
        return logger

    def _execute_stage(self, stage: Stage, video_id: UUID, use_cases: UseCases) -> None:
        res = use_cases.normalize_stage.execute(video_id)
        if res is not None:
            metadata = res.metadata
            self._logger.info(
                "Normalize metadata extracted",
                extra={
                    "video_id": str(video_id),
                    "width": metadata.width,
                    "height": metadata.height,
                    "duration_sec": metadata.duration_sec,
                    "fps": metadata.fps,
                    "nb_frames": metadata.nb_frames,
                },
            )
