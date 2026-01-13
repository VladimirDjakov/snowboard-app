"""Tests for storage backends."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from backend.app.adapters.storage import create_storage_backend
from backend.app.adapters.storage.local import LocalStorage
from backend.app.adapters.storage.s3 import S3Storage
from backend.app.application.ports.storage import PresignedUploadUrl
from backend.app.composition.settings import Settings


class TestLocalStorage:
    """Tests for LocalStorage."""

    def test_init_creates_base_directory(self, tmp_path: Path):
        """Test that initialization creates base directory."""
        storage_path = tmp_path.joinpath("storage")
        LocalStorage(storage_path)

        assert storage_path.exists()
        assert storage_path.is_dir()

    def test_generate_upload_url_creates_directory(self, tmp_path: Path):
        """Test that generate_upload_url creates directory for file."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "raw/video123/original.mp4"

        upload_info = backend.generate_upload_url(
            object_key=object_key,
            content_type="video/mp4",
            expires_in=3600,
        )

        # Check that directory was created
        file_path = backend._get_file_path(object_key)
        assert file_path.parent.exists()

        # Check UploadInfo
        assert isinstance(upload_info, PresignedUploadUrl)
        assert upload_info.method == "PUT"
        assert upload_info.object_key == object_key
        assert upload_info.expires_in_sec == 3600
        assert upload_info.headers["Content-Type"] == "video/mp4"
        assert "/api/v1/files/" in upload_info.url

    def test_generate_download_url(self, tmp_path: Path):
        """Test generate_download_url."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "proc/video123/normalized.mp4"

        url = backend.generate_download_url(object_key, expires_in=1800)

        assert "/api/v1/files/" in url
        assert object_key in url or "video123" in url

    def test_exists_file_exists(self, tmp_path: Path):
        """Test exists() when file exists."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "raw/video123/original.mp4"
        file_path = backend._get_file_path(object_key)

        # Create file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test content")

        assert backend.exists(object_key) is True

    def test_exists_file_not_exists(self, tmp_path: Path):
        """Test exists() when file does not exist."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "raw/video123/original.mp4"

        assert backend.exists(object_key) is False

    def test_delete_file(self, tmp_path: Path):
        """Test delete() removes file."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "raw/video123/original.mp4"
        file_path = backend._get_file_path(object_key)

        # Create file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("test content")

        backend.delete(object_key)

        assert not file_path.exists()

    def test_delete_file_not_exists(self, tmp_path: Path):
        """Test delete() raises FileNotFoundError when file doesn't exist."""
        backend = LocalStorage(tmp_path.joinpath("storage"))
        object_key = "raw/video123/original.mp4"

        with pytest.raises(FileNotFoundError):
            backend.delete(object_key)

    def test_get_file_path_normalizes_key(self, tmp_path: Path):
        """Test _get_file_path normalizes object key."""
        backend = LocalStorage(tmp_path.joinpath("storage"))

        # Test with leading slash
        path1 = backend._get_file_path("/raw/video123/file.mp4")
        path2 = backend._get_file_path("raw/video123/file.mp4")

        assert path1 == path2


class TestS3Storage:
    """Tests for S3Storage."""

    @pytest.fixture
    def mock_boto3_client(self):
        """Create a mock boto3 S3 client."""
        with patch("backend.app.adapters.storage.s3.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    def test_init_creates_s3_client(self, mock_boto3_client):
        """Test that initialization creates S3 client."""
        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        assert backend.client is not None
        assert backend.bucket_name == "test-bucket"

    def test_init_raises_import_error_without_boto3(self):
        """Test that initialization raises ImportError if boto3 is not available."""
        with patch("backend.app.adapters.storage.s3.boto3", None):
            with pytest.raises(ImportError, match="boto3 is required"):
                S3Storage(
                    endpoint_url="http://localhost:9000",
                    access_key_id="test-key",
                    secret_access_key="test-secret",
                    bucket_name="test-bucket",
                )

    def test_generate_upload_url(self, mock_boto3_client):
        """Test generate_upload_url creates presigned PUT URL."""
        mock_boto3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/presigned-url"
        )

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        upload_info = backend.generate_upload_url(
            object_key="raw/video123/original.mp4",
            content_type="video/mp4",
            expires_in=3600,
        )

        # Verify boto3 was called correctly
        mock_boto3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_boto3_client.generate_presigned_url.call_args
        assert call_kwargs[0][0] == "put_object"
        assert call_kwargs[1]["Params"]["Bucket"] == "test-bucket"
        assert call_kwargs[1]["Params"]["Key"] == "raw/video123/original.mp4"
        assert call_kwargs[1]["Params"]["ContentType"] == "video/mp4"
        assert call_kwargs[1]["ExpiresIn"] == 3600

        # Verify UploadInfo
        assert isinstance(upload_info, PresignedUploadUrl)
        assert upload_info.method == "PUT"
        assert upload_info.url == "https://s3.example.com/presigned-url"
        assert upload_info.headers["Content-Type"] == "video/mp4"

    def test_generate_download_url(self, mock_boto3_client):
        """Test generate_download_url creates presigned GET URL."""
        mock_boto3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/download-url"
        )

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        url = backend.generate_download_url("proc/video123/normalized.mp4", expires_in=1800)

        # Verify boto3 was called correctly
        mock_boto3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_boto3_client.generate_presigned_url.call_args
        assert call_kwargs[0][0] == "get_object"
        assert call_kwargs[1]["Params"]["Bucket"] == "test-bucket"
        assert call_kwargs[1]["Params"]["Key"] == "proc/video123/normalized.mp4"
        assert call_kwargs[1]["ExpiresIn"] == 1800

        assert url == "https://s3.example.com/download-url"

    def test_exists_file_exists(self, mock_boto3_client):
        """Test exists() when file exists."""
        # head_object doesn't raise exception when file exists
        mock_boto3_client.head_object.return_value = {}

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        assert backend.exists("raw/video123/original.mp4") is True
        mock_boto3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="raw/video123/original.mp4"
        )

    def test_exists_file_not_exists(self, mock_boto3_client):
        """Test exists() when file does not exist."""
        # head_object raises 404 ClientError when file doesn't exist
        error_response = {"Error": {"Code": "404"}}
        mock_boto3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        assert backend.exists("raw/video123/original.mp4") is False

    def test_exists_raises_other_errors(self, mock_boto3_client):
        """Test exists() re-raises non-404 errors."""
        # head_object raises other ClientError
        error_response = {"Error": {"Code": "403"}}
        mock_boto3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        with pytest.raises(ClientError):
            backend.exists("raw/video123/original.mp4")

    def test_delete(self, mock_boto3_client):
        """Test delete() removes file."""
        mock_boto3_client.delete_object.return_value = {}

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        backend.delete("raw/video123/original.mp4")

        mock_boto3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="raw/video123/original.mp4"
        )

    def test_delete_raises_error_on_failure(self, mock_boto3_client):
        """Test delete() raises RuntimeError on failure."""
        error_response = {"Error": {"Code": "403"}}
        mock_boto3_client.delete_object.side_effect = ClientError(error_response, "DeleteObject")

        backend = S3Storage(
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="test-bucket",
        )

        with pytest.raises(RuntimeError, match="Failed to delete"):
            backend.delete("raw/video123/original.mp4")


class TestStorageFactory:
    """Tests for create_storage_backend factory."""

    def test_create_local_storage(self):
        """Test creating LocalStorageBackend."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            storage_backend="local",
            storage_local_path="runtime/storage",
        )

        backend = create_storage_backend(settings)

        assert isinstance(backend, LocalStorage)
        assert backend.base_path.name == "storage"

    def test_create_s3_storage(self):
        """Test creating S3StorageBackend."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            storage_backend="s3",
            s3_endpoint_url="http://localhost:9000",
            s3_access_key_id="test-key",
            s3_secret_access_key="test-secret",
            s3_bucket_name="test-bucket",
        )

        with patch("backend.app.adapters.storage.s3.boto3"):
            backend = create_storage_backend(settings)
            assert isinstance(backend, S3Storage)
            assert backend.bucket_name == "test-bucket"

    def test_create_s3_storage_missing_endpoint(self):
        """Test that missing s3_endpoint_url raises Error."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                storage_backend="s3",
                s3_access_key_id="test-key",
                s3_secret_access_key="test-secret",
                s3_bucket_name="test-bucket",
            )

    def test_unknown_backend_validation(self):
        """Test that unknown storage_backend raises ValidationError from Pydantic."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                storage_backend="unknown",  # type: ignore
            )
