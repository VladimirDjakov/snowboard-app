"""Base worker logic shared across worker implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import Container, UseCases
from backend.app.presentation.bootstrap.settings import Settings, load_settings
from backend.app.presentation.workers.common.progress import ProgressReporter


class BaseWorker(ABC):
    """Shared worker lifecycle with wiring and progress tracking."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()

    def run_stage(self, stage: Stage, video_id: UUID) -> None:
        """Run a stage for a video with common wiring and lifecycle."""
        container = Container(self._settings)
        session = container.get_db_session()
        progress = ProgressReporter(stage=stage.value, video_id=video_id, logger=self._logger)

        try:
            use_cases = container.build_use_cases(session)
            progress.start()
            self._execute_stage(stage, video_id, use_cases)
            progress.finish()
        except Exception as exc:
            progress.fail(reason=str(exc))
            raise
        finally:
            session.close()
            container.close()

    @property
    @abstractmethod
    def _logger(self) -> logging.Logger:
        """Logger for progress reporting."""

    @abstractmethod
    def _execute_stage(self, stage: Stage, video_id: UUID, use_cases: UseCases) -> None:
        """Execute a stage using application use cases."""
