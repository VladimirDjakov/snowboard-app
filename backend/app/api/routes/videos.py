"""Video endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.api.controllers.videos_controller import VideosController, get_videos_controller
from backend.app.api.dependencies import get_use_cases
from backend.app.api.schemas.videos import (
    ArtifactResponse,
    CompleteUploadRequest,
    CompleteUploadResponse,
    CreateVideoRequest,
    CreateVideoResponse,
    VideoStatusResponse,
)

router = APIRouter()


@router.post("", response_model=CreateVideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    request_body: CreateVideoRequest,
    use_cases=Depends(get_use_cases),  # noqa: B008
    controller: VideosController = Depends(get_videos_controller),  # noqa: B008
):
    """
    Create a new video record and generate presigned upload URL.

    Creates a video record in the database and generates an upload URL
    for the client to upload the video file directly to storage.
    """
    return controller.create_video(use_cases=use_cases, request_body=request_body)


@router.post("/{video_id}/complete-upload", response_model=CompleteUploadResponse)
async def complete_upload(
    video_id: UUID,
    request_body: CompleteUploadRequest,
    use_cases=Depends(get_use_cases),  # noqa: B008
    controller: VideosController = Depends(get_videos_controller),  # noqa: B008
):
    """
    Confirm video upload completion and start processing pipeline.

    Verifies the share token and starts the analysis pipeline by calling StartAnalysis use case.
    """
    return controller.complete_upload(
        use_cases=use_cases,
        video_id=video_id,
        request_body=request_body,
    )


@router.get("/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: UUID,
    share_token: str = Query(..., description="Token for accessing video without auth"),
    use_cases=Depends(get_use_cases),  # noqa: B008
    controller: VideosController = Depends(get_videos_controller),  # noqa: B008
):
    """
    Get video processing status and progress.

    Returns the current status of video processing, including stage progress
    and available artifacts.
    """
    return controller.get_video_status(
        use_cases=use_cases,
        video_id=video_id,
        share_token=share_token,
    )


@router.get("/{video_id}/artifacts", response_model=ArtifactResponse)
async def get_video_artifacts(
    video_id: UUID,
    share_token: str = Query(..., description="Token for accessing video without auth"),
    use_cases=Depends(get_use_cases),  # noqa: B008
    controller: VideosController = Depends(get_videos_controller),  # noqa: B008
):
    """
    Get list of video artifacts.

    Returns all artifacts associated with the video, including download URLs.
    """
    return controller.get_video_artifacts(
        use_cases=use_cases,
        video_id=video_id,
        share_token=share_token,
    )
