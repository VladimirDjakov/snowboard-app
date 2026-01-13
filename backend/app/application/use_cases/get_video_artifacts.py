"""Use case: Get video artifacts + download URLs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.app.application.ports.storage import Storage
from backend.app.application.ports.video_repo import VideoRepo
from backend.app.application.use_cases.list_artifacts import ListArtifacts
from backend.app.domain.value_objects import ArtifactRef


@dataclass(frozen=True, slots=True)
class VideoArtifactResult:
    kind: str
    version: str
    url: str
    expires_in_sec: int


class GetVideoArtifacts:
    """Return all artifacts for a video with presigned download URLs."""

    def __init__(
        self,
        video_repo: VideoRepo,
        list_artifacts: ListArtifacts,
        storage: Storage,
        *,
        download_url_ttl_sec: int = 900,
    ) -> None:
        self._video_repo = video_repo
        self._list_artifacts = list_artifacts
        self._storage = storage
        self._download_url_ttl_sec = download_url_ttl_sec

    def execute(self, *, video_id: UUID, share_token: str) -> list[VideoArtifactResult]:
        video = self._video_repo.get(video_id)
        if video is None:
            raise ValueError(f"Video {video_id} not found")
        if video.share_token != share_token:
            raise PermissionError("Invalid share token")

        artifacts_list: list[ArtifactRef] = self._list_artifacts.execute(video_id) or []
        results: list[VideoArtifactResult] = []
        for artifact in artifacts_list:
            url = self._storage.generate_download_url(
                object_key=artifact.object_key,
                expires_in=self._download_url_ttl_sec,
            )
            results.append(
                VideoArtifactResult(
                    kind=artifact.kind.value,
                    version=artifact.version,
                    url=url,
                    expires_in_sec=self._download_url_ttl_sec,
                )
            )
        return results
