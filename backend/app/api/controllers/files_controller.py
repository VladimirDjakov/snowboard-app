"""HTTP controller for file endpoints (storage access via ports)."""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import Depends, HTTPException, Request, Response, status

from backend.app.api.dependencies import get_storage
from backend.app.application.ports.storage import Storage


def _guess_content_type(object_key: str) -> str:
    if object_key.endswith(".mp4"):
        return "video/mp4"
    if object_key.endswith(".jsonl"):
        return "application/x-ndjson"
    if object_key.endswith(".json"):
        return "application/json"
    return "application/octet-stream"


class FilesController:
    """Thin controller for file read/write over HTTP."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def get_file(self, *, key: str) -> Response:
        decoded_key = unquote(key)

        if not self._storage.exists(decoded_key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {decoded_key}",
            )

        try:
            file_data = self._storage.read_file(decoded_key)
        except FileNotFoundError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {decoded_key}",
            ) from err

        content_type = _guess_content_type(decoded_key)
        filename = decoded_key.split("/")[-1] if decoded_key else "file"

        return Response(
            content=file_data,
            media_type=content_type,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    async def upload_file(self, *, key: str, request: Request) -> dict[str, str]:
        decoded_key = unquote(key)
        file_data = await request.body()
        content_type = request.headers.get("Content-Type", "application/octet-stream")

        try:
            self._storage.write_file(
                object_key=decoded_key,
                data=file_data,
                content_type=content_type,
            )
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(err)}",
            ) from err

        return {"status": "ok", "object_key": decoded_key}


def get_files_controller(
    storage: Storage = Depends(get_storage),  # noqa: B008
) -> FilesController:
    """Dependency factory for FilesController."""

    return FilesController(storage=storage)
