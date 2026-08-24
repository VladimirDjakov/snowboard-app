"""CPU worker orchestration for processing stages."""

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import UseCases
from backend.app.presentation.workers.common.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class CPUWorker(BaseWorker):
    """Run CPU-bound stages with shared wiring and lifecycle."""

    @property
    def _logger(self):
        return logger

    def _execute_stage(self, stage: Stage, video_id: UUID, use_cases: UseCases) -> None:
        match stage:
            case Stage.TRANSCODE:
                self._transcode_stage(video_id, use_cases)
            case Stage.FEATURES:
                self._features_stage(video_id, use_cases)
            case Stage.FEEDBACK:
                self._feedback_stage(video_id, use_cases)
            case _:
                raise ValueError(f"Unsupported stage: {stage}")

    def _transcode_stage(self, video_id: UUID, use_cases: UseCases) -> None:
        """Execute a CPU stage using application use cases."""
        outcome = use_cases.transcode_stage.execute(video_id)
        if outcome is not None:
            metadata = outcome.metadata
            self._logger.info(
                "Transcode metadata extracted",
                extra={
                    "video_id": str(video_id),
                    "width": metadata.width,
                    "height": metadata.height,
                    "duration_sec": metadata.duration_sec,
                    "fps": metadata.fps,
                    "nb_frames": metadata.nb_frames,
                },
            )

    def _features_stage(self, video_id: UUID, use_cases: UseCases) -> None:
        """Execute a CPU stage using application use cases."""
        raise NotImplementedError("Features stage is not implemented for CPU worker")

    def _feedback_stage(self, video_id: UUID, use_cases: UseCases) -> None:
        """Execute a CPU stage using application use cases."""
        raise NotImplementedError("Feedback stage is not implemented for CPU worker")
