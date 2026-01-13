"""HTTP controller for video endpoints (maps exceptions, delegates to use cases)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from backend.app.presentation.api.presenters.videos_presenter import VideosPresenter
from backend.app.presentation.api.schemas.videos import CompleteUploadRequest, CreateVideoRequest
from backend.app.presentation.bootstrap.container import UseCases


def _is_not_found(err: Exception) -> bool:
    msg = str(err).lower()
    return "not found" in msg


class VideosController:
    """Thin controller: call use cases and return already-built API models."""

    def __init__(self, presenter: VideosPresenter | None = None) -> None:
        self._presenter = presenter or VideosPresenter()

    def create_video(self, *, use_cases: UseCases, request_body: CreateVideoRequest):
        try:
            result = use_cases.create_video.execute(
                filename=request_body.filename,
                content_type=request_body.content_type,
                size_bytes=request_body.size_bytes,
            )
            return self._presenter.present_create_video(result)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    def complete_upload(
        self,
        *,
        use_cases: UseCases,
        video_id: UUID,
        request_body: CompleteUploadRequest,
    ):
        try:
            result = use_cases.complete_upload.execute(
                video_id=video_id, share_token=request_body.share_token
            )
            return self._presenter.present_complete_upload(result)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
        except ValueError as err:
            code = status.HTTP_404_NOT_FOUND if _is_not_found(err) else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=code, detail=str(err)) from err
        except RuntimeError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(err),
            ) from err

    def get_video_status(self, *, use_cases: UseCases, video_id: UUID, share_token: str):
        try:
            result = use_cases.get_video_status.execute(video_id=video_id, share_token=share_token)
            return self._presenter.present_video_status(result)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err

    def get_video_artifacts(self, *, use_cases: UseCases, video_id: UUID, share_token: str):
        try:
            artifacts = use_cases.get_video_artifacts.execute(
                video_id=video_id, share_token=share_token
            )
            return self._presenter.present_artifacts_for_video(video_id, artifacts)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


def get_videos_controller() -> VideosController:
    """Dependency factory for VideosController."""

    return VideosController()
