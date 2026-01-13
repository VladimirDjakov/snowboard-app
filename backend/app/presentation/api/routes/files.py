"""File endpoints for local storage."""

from fastapi import APIRouter, Depends, Request

from backend.app.presentation.api.controllers.files_controller import (
    FilesController,
    get_files_controller,
)

router = APIRouter()


@router.get("/{key:path}")
async def get_file(
    key: str,
    controller: FilesController = Depends(get_files_controller),  # noqa: B008
):
    """
    Download a file from storage.

    For local storage, serves files directly from the filesystem.
    The key should be URL-encoded (e.g., 'raw/{video_id}/original.mp4').
    """
    return await controller.get_file(key=key)


@router.put("/{key:path}")
async def upload_file(
    key: str,
    request: Request,
    controller: FilesController = Depends(get_files_controller),  # noqa: B008
):
    """
    Upload a file to storage.

    For local storage, accepts file upload and saves it to the filesystem.
    The key should be URL-encoded in the path (e.g., 'raw/{video_id}/original.mp4').
    """
    return await controller.upload_file(key=key, request=request)
