"""Integration tests for video API endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.application.dtos import StageView
from backend.app.application.interfaces.storage import PresignedUploadUrl
from backend.app.application.use_cases.video import (
    ArtifactWithUrl,
    CompleteUploadResult,
    CreateVideoResult,
    VideoArtifactResult,
    VideoStatusResult,
)
from backend.app.presentation.api.dependencies import get_use_cases
from backend.app.presentation.bootstrap.container import UseCases


@pytest.fixture
def mock_container():
    """Create a mock container."""
    # Container is no longer needed for videos tests because we override get_use_cases dependency.
    container = MagicMock()
    container.storage = MagicMock()
    container.get_session = MagicMock()
    container.build_use_cases = MagicMock()
    return container


@pytest.fixture
def mock_use_cases():
    """Create mock use cases."""
    use_cases = MagicMock(spec=UseCases)
    use_cases.create_video = MagicMock()
    use_cases.complete_upload = MagicMock()
    use_cases.get_video_status = MagicMock()
    use_cases.get_video_artifacts = MagicMock()
    return use_cases


@pytest.fixture
def app_with_container(mock_container):
    """Create FastAPI app with mocked container."""
    # Mock storage factory for API tests (but not for test_storage.py)
    with patch(
        "backend.app.infrastructure.storage.create_storage_backend",
        return_value=MagicMock(),
    ):
        # Create a fresh app instance to ensure routes are registered
        from fastapi import FastAPI

        from backend.app.presentation.api.routes import files, health, videos

        app = FastAPI(
            title="Snowboard Coach API",
            description="API for snowboard video analysis pipeline",
            version="0.1.0",
        )

        # Register routers explicitly (matching main.py)
        app.include_router(health.router, tags=["health"])
        app.include_router(videos.router, prefix="/v1/videos", tags=["videos"])
        app.include_router(files.router, prefix="/api/v1/files", tags=["files"])

        # Set container in app state
        app.state.container = mock_container

        return app


@pytest.fixture
def client(app_with_container, mock_use_cases):
    """Create test client with overridden get_use_cases dependency."""

    def get_use_cases_override(request: Request):
        yield mock_use_cases

    app_with_container.dependency_overrides[get_use_cases] = get_use_cases_override
    yield TestClient(app_with_container)
    app_with_container.dependency_overrides.clear()


class TestCreateVideo:
    """Tests for POST /v1/videos endpoint."""

    def test_routes_registered(self, app_with_container):
        """Test that routes are properly registered."""
        route_paths = []
        for route in app_with_container.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                route_paths.append((route.path, list(route.methods)))

        # Check that video routes are registered
        video_routes = [path for path, methods in route_paths if "/videos" in path]
        assert len(video_routes) > 0, f"Video routes not found. Available routes: {route_paths}"

    def test_create_video_success(self, client, mock_use_cases):
        """Test successful video creation."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        upload = PresignedUploadUrl(
            method="PUT",
            url=f"http://localhost:8000/api/v1/files/raw/{video_id}/original.mp4",
            headers={"Content-Type": "video/mp4"},
            storage_path=f"raw/{video_id}/original.mp4",
            expires_in_sec=3600,
        )
        mock_use_cases.create_video.execute.return_value = CreateVideoResult(
            video_id=video_id,
            share_token=share_token,
            upload=upload,
            max_duration_sec=120,
            max_size_bytes=500000000,
        )

        response = client.post(
            "/v1/videos",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024000,
            },
        )

        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert data["share_token"] == share_token
        assert data["upload"]["method"] == "PUT"
        assert data["upload"]["storage_path"] == f"raw/{video_id}/original.mp4"
        assert data["limits"]["max_duration_sec"] == 120
        assert data["limits"]["max_size_bytes"] == 500000000
        mock_use_cases.create_video.execute.assert_called_once()

    def test_create_video_without_size(self, client, mock_use_cases):
        """Test video creation without size_bytes."""
        video_id = uuid4()
        share_token = "st_test_token_456"

        upload = PresignedUploadUrl(
            method="PUT",
            url=f"http://localhost:8000/api/v1/files/raw/{video_id}/original.mp4",
            headers={"Content-Type": "video/mp4"},
            storage_path=f"raw/{video_id}/original.mp4",
            expires_in_sec=3600,
        )
        mock_use_cases.create_video.execute.return_value = CreateVideoResult(
            video_id=video_id,
            share_token=share_token,
            upload=upload,
            max_duration_sec=120,
            max_size_bytes=500000000,
        )

        response = client.post(
            "/v1/videos",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == str(video_id)


class TestCompleteUpload:
    """Tests for POST /v1/videos/{id}/complete-upload endpoint."""

    def test_complete_upload_success(self, client, mock_use_cases):
        """Test successful upload completion."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        mock_use_cases.complete_upload.execute.return_value = CompleteUploadResult(
            video_id=video_id,
            status="created",
            job_id=video_id,
            pipeline_version="mvp_v1",
            stages=[
                StageView(name="normalize", status="queued"),
                StageView(name="pose", status="pending"),
                StageView(name="features", status="pending"),
                StageView(name="feedback", status="pending"),
            ],
        )

        response = client.post(
            f"/v1/videos/{video_id}/complete-upload",
            json={"share_token": share_token},
        )

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert data["status"] == "created"
        assert data["pipeline_version"] == "mvp_v1"
        assert len(data["stages"]) == 4  # NORMALIZE, POSE, FEATURES, FEEDBACK

        mock_use_cases.complete_upload.execute.assert_called_once()

    def test_complete_upload_video_not_found(self, client, mock_use_cases):
        """Test upload completion with non-existent video."""
        video_id = uuid4()
        mock_use_cases.complete_upload.execute.side_effect = ValueError("Video not found")

        response = client.post(
            f"/v1/videos/{video_id}/complete-upload",
            json={"share_token": "st_test_token"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_complete_upload_invalid_token(self, client, mock_use_cases):
        """Test upload completion with invalid share token."""
        video_id = uuid4()
        mock_use_cases.complete_upload.execute.side_effect = PermissionError("Invalid share token")

        response = client.post(
            f"/v1/videos/{video_id}/complete-upload",
            json={"share_token": "st_wrong_token"},
        )

        assert response.status_code == 403
        assert "Invalid share token" in response.json()["detail"]

    def test_complete_upload_start_analysis_error(self, client, mock_use_cases):
        """Test upload completion when StartAnalysis raises error."""
        video_id = uuid4()
        share_token = "st_test_token_123"
        mock_use_cases.complete_upload.execute.side_effect = ValueError("Cannot start analysis")

        response = client.post(
            f"/v1/videos/{video_id}/complete-upload",
            json={"share_token": share_token},
        )

        assert response.status_code == 400
        assert "Cannot start analysis" in response.json()["detail"]


class TestGetVideoStatus:
    """Tests for GET /v1/videos/{id} endpoint."""

    def test_get_video_status_with_job(self, client, mock_use_cases):
        """Test getting video status when job exists."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        mock_use_cases.get_video_status.execute.return_value = VideoStatusResult(
            video_id=video_id,
            status="running",
            pipeline_version="mvp_v1",
            progress_pct=0.25,
            current_stage="pose",
            updated_at=datetime.now(UTC),
            stages=[
                StageView(name="normalize", status="done"),
                StageView(name="pose", status="running"),
                StageView(name="features", status="pending"),
                StageView(name="feedback", status="pending"),
            ],
            artifacts=[
                ArtifactWithUrl(
                    kind="normalized",
                    version="v1",
                    url=f"http://localhost:8000/api/v1/files/proc/{video_id}/normalized.mp4",
                    expires_in_sec=900,
                )
            ],
            errors=[],
        )

        response = client.get(f"/v1/videos/{video_id}?share_token={share_token}")

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert data["status"] == "running"
        assert data["pipeline_version"] == "mvp_v1"
        assert len(data["stages"]) == 4
        assert data["progress"]["pct"] == 0.25  # 1 out of 4 stages done

    def test_get_video_status_without_job(self, client, mock_use_cases):
        """Test getting video status when job doesn't exist yet."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        mock_use_cases.get_video_status.execute.return_value = VideoStatusResult(
            video_id=video_id,
            status="created",
            pipeline_version="mvp_v1",
            progress_pct=0.0,
            current_stage="normalize",
            updated_at=datetime.now(UTC),
            stages=[
                StageView(name="normalize", status="pending"),
                StageView(name="pose", status="pending"),
                StageView(name="features", status="pending"),
                StageView(name="feedback", status="pending"),
            ],
            artifacts=[],
            errors=[],
        )

        response = client.get(f"/v1/videos/{video_id}?share_token={share_token}")

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert data["status"] == "created"
        assert data["progress"]["pct"] == 0.0

    def test_get_video_status_not_found(self, client, mock_use_cases):
        """Test getting status for non-existent video."""
        video_id = uuid4()
        mock_use_cases.get_video_status.execute.side_effect = ValueError("Video not found")

        response = client.get(f"/v1/videos/{video_id}?share_token=st_test_token")

        assert response.status_code == 404

    def test_get_video_status_invalid_token(self, client, mock_use_cases):
        """Test getting status with invalid share token."""
        video_id = uuid4()
        mock_use_cases.get_video_status.execute.side_effect = PermissionError("Invalid share token")

        response = client.get(f"/v1/videos/{video_id}?share_token=st_wrong_token")

        assert response.status_code == 403


class TestGetVideoArtifacts:
    """Tests for GET /v1/videos/{id}/artifacts endpoint."""

    def test_get_artifacts_success(self, client, mock_use_cases):
        """Test successful artifact retrieval."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        mock_use_cases.get_video_artifacts.execute.return_value = [
            VideoArtifactResult(
                kind="normalized",
                version="v1",
                url=f"http://localhost:8000/api/v1/files/proc/{video_id}/normalized.mp4",
                expires_in_sec=900,
            ),
            VideoArtifactResult(
                kind="keypoints",
                version="v1",
                url=f"http://localhost:8000/api/v1/files/proc/{video_id}/keypoints_v1.jsonl",
                expires_in_sec=900,
            ),
        ]

        response = client.get(f"/v1/videos/{video_id}/artifacts?share_token={share_token}")

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert len(data["artifacts"]) == 2
        assert data["artifacts"][0]["kind"] == "normalized"
        assert data["artifacts"][1]["kind"] == "keypoints"

    def test_get_artifacts_empty(self, client, mock_use_cases):
        """Test artifact retrieval when no artifacts exist."""
        video_id = uuid4()
        share_token = "st_test_token_123"

        mock_use_cases.get_video_artifacts.execute.return_value = []

        response = client.get(f"/v1/videos/{video_id}/artifacts?share_token={share_token}")

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(video_id)
        assert len(data["artifacts"]) == 0

    def test_get_artifacts_not_found(self, client, mock_use_cases):
        """Test artifact retrieval for non-existent video."""
        video_id = uuid4()
        mock_use_cases.get_video_artifacts.execute.side_effect = ValueError("Video not found")

        response = client.get(f"/v1/videos/{video_id}/artifacts?share_token=st_test_token")

        assert response.status_code == 404

    def test_get_artifacts_invalid_token(self, client, mock_use_cases):
        """Test artifact retrieval with invalid share token."""
        video_id = uuid4()
        mock_use_cases.get_video_artifacts.execute.side_effect = PermissionError(
            "Invalid share token"
        )

        response = client.get(f"/v1/videos/{video_id}/artifacts?share_token=st_wrong_token")

        assert response.status_code == 403
