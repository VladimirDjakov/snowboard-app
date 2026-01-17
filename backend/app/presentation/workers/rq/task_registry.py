"""Task registry for RQ workers."""

from backend.app.domain.analysis_job import Stage

TASK_MAP: dict[Stage, str] = {
    Stage.NORMALIZE: "backend.app.presentation.workers.rq.handlers.normalize_task",
    Stage.POSE: "backend.app.presentation.workers.rq.handlers.pose_task",
    Stage.FEATURES: "backend.app.presentation.workers.rq.handlers.features_task",
    Stage.FEEDBACK: "backend.app.presentation.workers.rq.handlers.feedback_task",
}

__all__ = ["TASK_MAP"]
