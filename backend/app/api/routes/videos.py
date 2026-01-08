"""Video endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_video():
    """Create a new video record and generate presigned upload URL."""
    # TODO: Implement video creation logic
    return {"message": "Not implemented yet"}


@router.post("/{video_id}/complete-upload")
async def complete_upload(video_id: str):
    """Confirm video upload completion and start processing pipeline."""
    # TODO: Implement upload completion logic
    return {"message": "Not implemented yet", "video_id": video_id}


@router.get("/{video_id}")
async def get_video_status(video_id: str):
    """Get video processing status and progress."""
    # TODO: Implement status retrieval logic
    return {"message": "Not implemented yet", "video_id": video_id}


@router.get("/{video_id}/artifacts")
async def get_video_artifacts(video_id: str):
    """Get list of video artifacts."""
    # TODO: Implement artifacts retrieval logic
    return {"message": "Not implemented yet", "video_id": video_id}
