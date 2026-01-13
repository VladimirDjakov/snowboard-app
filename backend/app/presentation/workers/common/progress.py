"""Progress reporting helpers for workers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID


class ProgressReporter:
    """Structured progress logger for worker stages."""

    def __init__(
        self,
        *,
        stage: str,
        video_id: UUID | str,
        total: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.stage = stage
        self.video_id = str(video_id)
        self.total = total
        self._current = 0
        self._logger = logger or logging.getLogger(__name__)

    def start(self, message: str = "stage_started") -> None:
        """Log start of a stage."""
        self._log(message, current=0)

    def advance(self, current: int, message: str = "stage_progress") -> None:
        """Log progress update with current counter."""
        self._current = current
        self._log(message, current=current)

    def finish(self, message: str = "stage_completed") -> None:
        """Log successful completion."""
        current = self.total if self.total is not None else self._current
        self._log(message, current=current)

    def fail(self, message: str = "stage_failed", *, reason: str | None = None) -> None:
        """Log failure with optional reason."""
        extra: dict[str, Any] = {}
        if reason:
            extra["reason"] = reason
        self._log(message, current=self._current, extra=extra, level="error")

    def _log(
        self,
        message: str,
        *,
        current: int | None,
        extra: dict[str, Any] | None = None,
        level: str = "info",
    ) -> None:
        payload: dict[str, Any] = {
            "video_id": self.video_id,
            "stage": self.stage,
            "current": current,
            "total": self.total,
        }
        if current is not None and self.total:
            payload["progress"] = round((current / self.total) * 100, 2)
        if extra:
            payload.update(extra)

        log_fn = getattr(self._logger, level, self._logger.info)
        log_fn(message, extra=payload)
