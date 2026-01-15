"""Transcode worker entrypoint for CPU queue."""

from __future__ import annotations

import logging
from uuid import UUID

from backend.app.domain.analysis_job import Stage
from backend.app.presentation.bootstrap.container import Container
from backend.app.presentation.bootstrap.settings import load_settings
from backend.app.presentation.workers.common.progress import ProgressReporter

logger = logging.getLogger(__name__)


def run_transcode(video_id: UUID | str) -> None:
    """Run the transcode stage for a video."""
    video_uuid = UUID(str(video_id))
    settings = load_settings()
    container = Container(settings)
    session = container.get_session()
    use_cases = None
    progress = ProgressReporter(stage=Stage.TRANSCODE.value, video_id=video_uuid, logger=logger)

    try:
        use_cases = container.build_use_cases(session)
        progress.start()
        outcome = use_cases.transcode_stage.execute(video_uuid)
        if outcome is not None:
            metadata = outcome.metadata
            logger.info(
                "Transcode metadata extracted",
                extra={
                    "video_id": str(video_uuid),
                    "width": metadata.width,
                    "height": metadata.height,
                    "duration_sec": metadata.duration_sec,
                    "fps": metadata.fps,
                    "nb_frames": metadata.nb_frames,
                },
            )
        progress.finish()
    except Exception as exc:
        progress.fail(reason=str(exc))
        raise
    finally:
        session.close()
        container.close()
