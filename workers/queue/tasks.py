"""RQ task definitions for video processing pipeline."""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def transcode_task(video_id: str) -> None:
    """
    Transcode task - normalizes video to standard format.

    This task will be implemented in Phase 7.
    For now, it's a placeholder that logs the execution.

    Args:
        video_id: UUID of the video to transcode (as string)
    """
    video_uuid = UUID(video_id)
    logger.info("Transcode task started", extra={"video_id": str(video_uuid)})

    # TODO: Phase 7 - Implement transcode logic
    # 1. Read original video from storage
    # 2. Normalize via ffmpeg (resolution, FPS, codec)
    # 3. Extract metadata (duration, fps, dimensions)
    # 4. Save normalized.mp4 to storage
    # 5. Update status in DB
    # 6. Enqueue pose task

    logger.info("Transcode task completed (placeholder)", extra={"video_id": str(video_uuid)})


def pose_task(video_id: str) -> None:
    """
    Pose inference task - extracts keypoints from video using Triton.

    This task will be implemented in Phase 8.
    For now, it's a placeholder that logs the execution.

    Args:
        video_id: UUID of the video to process (as string)
    """
    video_uuid = UUID(video_id)
    logger.info("Pose task started", extra={"video_id": str(video_uuid)})

    # TODO: Phase 8 - Implement pose inference logic
    # 1. Read normalized.mp4 from storage
    # 2. Process video in batches through Triton
    # 3. Write keypoints_v1.jsonl (streaming, JSONL format)
    # 4. Update progress (by frames)
    # 5. Save keypoints_v1.jsonl to storage
    # 6. Enqueue features task

    logger.info("Pose task completed (placeholder)", extra={"video_id": str(video_uuid)})


def features_task(video_id: str) -> None:
    """
    Features extraction task - computes metrics from keypoints.

    This task will be implemented in Phase 9.
    For now, it's a placeholder that logs the execution.

    Args:
        video_id: UUID of the video to process (as string)
    """
    video_uuid = UUID(video_id)
    logger.info("Features task started", extra={"video_id": str(video_uuid)})

    # TODO: Phase 9 - Implement features extraction logic
    # 1. Read keypoints_v1.jsonl from storage
    # 2. Compute metrics:
    #    - Knee angles (knee_flex_deg)
    #    - Torso lean (torso_lean_deg)
    #    - Distance between feet
    #    - Other metrics from schema
    # 3. Smooth time series
    # 4. Aggregate by segments
    # 5. Save features_v1.json to storage
    # 6. Enqueue feedback task

    logger.info("Features task completed (placeholder)", extra={"video_id": str(video_uuid)})


def feedback_task(video_id: str) -> None:
    """
    Feedback generation task - applies rule-based rules to features.

    This task will be implemented in Phase 10.
    For now, it's a placeholder that logs the execution.

    Args:
        video_id: UUID of the video to process (as string)
    """
    video_uuid = UUID(video_id)
    logger.info("Feedback task started", extra={"video_id": str(video_uuid)})

    # TODO: Phase 10 - Implement feedback generation logic
    # 1. Read features_v1.json from storage
    # 2. Read rules from rules/feedback/v1.yaml
    # 3. Apply rules to metrics
    # 4. Generate feedback items (severity, title, detail, t_ranges)
    # 5. Save feedback_v1.json to storage
    # 6. Update video status: completed

    logger.info("Feedback task completed (placeholder)", extra={"video_id": str(video_uuid)})
