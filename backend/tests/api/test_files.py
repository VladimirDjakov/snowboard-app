"""Integration tests for file API endpoints."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.presentation.bootstrap.container import Container


@pytest.fixture
def mock_container():
    """Create a mock container."""
    container = MagicMock(spec=Container)
    container.storage = MagicMock()
    return container


@pytest.fixture
def app_with_container(mock_container):
    """Create FastAPI app with mocked container."""
    # Mock storage factory for API tests
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
def client(app_with_container):
    """Create test client."""
    return TestClient(app_with_container)


class TestGetFile:
    """Tests for GET /api/v1/files/{key} endpoint."""

    def test_get_file_success_mp4(self, client, mock_container):
        """Test successful file download for MP4 file."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"
        file_data = b"fake video content"

        mock_container.storage.exists.return_value = True
        mock_container.storage.read_file.return_value = file_data

        response = client.get(f"/api/v1/files/{storage_path}")

        assert response.status_code == 200
        assert response.content == file_data
        assert response.headers["content-type"] == "video/mp4"
        assert (
            f'filename="{storage_path.split("/")[-1]}"' in response.headers["content-disposition"]
        )

        mock_container.storage.exists.assert_called_once_with(storage_path)
        mock_container.storage.read_file.assert_called_once_with(storage_path)

    def test_get_file_success_jsonl(self, client, mock_container):
        """Test successful file download for JSONL file."""
        video_id = uuid4()
        storage_path = f"proc/{video_id}/keypoints_v1.jsonl"
        file_data = b'{"frame": 1}\n{"frame": 2}\n'

        mock_container.storage.exists.return_value = True
        mock_container.storage.read_file.return_value = file_data

        response = client.get(f"/api/v1/files/{storage_path}")

        assert response.status_code == 200
        assert response.content == file_data
        assert response.headers["content-type"] == "application/x-ndjson"

    def test_get_file_success_json(self, client, mock_container):
        """Test successful file download for JSON file."""
        video_id = uuid4()
        storage_path = f"proc/{video_id}/features_v1.json"
        file_data = b'{"feature": "value"}'

        mock_container.storage.exists.return_value = True
        mock_container.storage.read_file.return_value = file_data

        response = client.get(f"/api/v1/files/{storage_path}")

        assert response.status_code == 200
        assert response.content == file_data
        assert response.headers["content-type"] == "application/json"

    def test_get_file_not_found(self, client, mock_container):
        """Test file download when file doesn't exist."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"

        mock_container.storage.exists.return_value = False

        response = client.get(f"/api/v1/files/{storage_path}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_read_error(self, client, mock_container):
        """Test file download when read fails."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"

        mock_container.storage.exists.return_value = True
        mock_container.storage.read_file.side_effect = FileNotFoundError("File not found")

        response = client.get(f"/api/v1/files/{storage_path}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_url_encoded_key(self, client, mock_container):
        """Test file download with URL-encoded key."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original video.mp4"
        encoded_key = "raw%2F" + str(video_id) + "%2Foriginal%20video.mp4"
        file_data = b"fake video content"

        mock_container.storage.exists.return_value = True
        mock_container.storage.read_file.return_value = file_data

        response = client.get(f"/api/v1/files/{encoded_key}")

        assert response.status_code == 200
        # Verify that decoded key was used
        mock_container.storage.exists.assert_called_once_with(storage_path)
        mock_container.storage.read_file.assert_called_once_with(storage_path)


class TestUploadFile:
    """Tests for PUT /api/v1/files/{key} endpoint."""

    def test_upload_file_success(self, client, mock_container):
        """Test successful file upload."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"
        file_data = b"fake video content"

        response = client.put(
            f"/api/v1/files/{storage_path}",
            content=file_data,
            headers={"Content-Type": "video/mp4"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["storage_path"] == storage_path

        mock_container.storage.write_file.assert_called_once_with(
            storage_path=storage_path,
            data=file_data,
            content_type="video/mp4",
        )

    def test_upload_file_default_content_type(self, client, mock_container):
        """Test file upload without Content-Type header."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"
        file_data = b"fake video content"

        response = client.put(
            f"/api/v1/files/{storage_path}",
            content=file_data,
        )

        assert response.status_code == 200
        mock_container.storage.write_file.assert_called_once_with(
            storage_path=storage_path,
            data=file_data,
            content_type="application/octet-stream",
        )

    def test_upload_file_url_encoded_key(self, client, mock_container):
        """Test file upload with URL-encoded key."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original video.mp4"
        encoded_key = "raw%2F" + str(video_id) + "%2Foriginal%20video.mp4"
        file_data = b"fake video content"

        response = client.put(
            f"/api/v1/files/{encoded_key}",
            content=file_data,
            headers={"Content-Type": "video/mp4"},
        )

        assert response.status_code == 200
        # Verify that decoded key was used
        mock_container.storage.write_file.assert_called_once_with(
            storage_path=storage_path,
            data=file_data,
            content_type="video/mp4",
        )

    def test_upload_file_storage_error(self, client, mock_container):
        """Test file upload when storage write fails."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"
        file_data = b"fake video content"

        mock_container.storage.write_file.side_effect = Exception("Storage error")

        response = client.put(
            f"/api/v1/files/{storage_path}",
            content=file_data,
            headers={"Content-Type": "video/mp4"},
        )

        assert response.status_code == 500
        assert "Failed to upload file" in response.json()["detail"]

    def test_upload_file_empty_content(self, client, mock_container):
        """Test file upload with empty content."""
        video_id = uuid4()
        storage_path = f"raw/{video_id}/original.mp4"
        file_data = b""

        response = client.put(
            f"/api/v1/files/{storage_path}",
            content=file_data,
            headers={"Content-Type": "video/mp4"},
        )

        assert response.status_code == 200
        mock_container.storage.write_file.assert_called_once_with(
            storage_path=storage_path,
            data=file_data,
            content_type="video/mp4",
        )
