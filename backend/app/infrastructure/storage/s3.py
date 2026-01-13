"""S3/MinIO storage backend implementation."""

from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from backend.app.application.interfaces.storage import PresignedUploadUrl
from backend.app.infrastructure.storage.base import BaseStorage


class S3Storage(BaseStorage):
    """S3/MinIO storage backend for production."""

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "ru-msk-1",
        expires_in: int = 3600,
    ):
        """
        Initialize S3 storage backend.

        Args:
            endpoint_url: S3 endpoint URL (e.g., 'http://localhost:9000' for MinIO)
            access_key_id: S3 access key ID
            secret_access_key: S3 secret access key
            bucket_name: S3 bucket name
            region: S3 region (default: 'ru-msk-1')
            expires_in: Default expiration time for presigned URLs in seconds

        Raises:
            ImportError: If boto3 is not installed
        """
        if boto3 is None:
            raise ImportError(
                "boto3 is required for S3StorageBackend. Install it with: pip install boto3"
            )

        self.bucket_name = bucket_name
        self.expires_in = expires_in

        # Create S3 client
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    def generate_upload_url(
        self,
        storage_path: str,
        content_type: str,
        expires_in: int | None = None,
    ) -> PresignedUploadUrl:
        """
        Generate presigned URL for uploading to S3.

        Args:
            storage_path: Storage path to the artifact
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds (uses default if None)

        Returns:
            PresignedUploadUrl with presigned PUT URL
        """
        if expires_in is None:
            expires_in = self.expires_in

        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_path,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

        return PresignedUploadUrl(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
            storage_path=storage_path,
            expires_in_sec=expires_in,
        )

    def generate_download_url(
        self,
        storage_path: str,
        expires_in: int | None = None,
    ) -> str:
        """
        Generate presigned URL for downloading from S3.

        Args:
            storage_path: Storage path to the artifact
            expires_in: URL expiration time in seconds (uses default if None)

        Returns:
            Presigned GET URL
        """
        if expires_in is None:
            expires_in = self.expires_in

        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_path,
            },
            ExpiresIn=expires_in,
        )

    def exists(self, storage_path: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except ClientError as e:
            # 404 means file doesn't exist
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return False
            # Re-raise other errors
            raise

    def delete(self, storage_path: str) -> None:
        """
        Delete file from S3.

        Args:
            storage_path: Storage path to the artifact

        Raises:
            ClientError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_path)
        except ClientError as e:
            # Re-raise with more context
            raise RuntimeError(f"Failed to delete object {storage_path}: {e}") from e

    def read_file(self, storage_path: str) -> bytes:
        """
        Read file from S3.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=storage_path)
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {storage_path}") from e
            # Re-raise other errors
            raise RuntimeError(f"Failed to read object {storage_path}: {e}") from e

    def write_file(
        self,
        storage_path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        """
        Write file to S3.

        Args:
            storage_path: Storage path to the artifact
            data: File contents as bytes
            content_type: MIME type of the file
        """
        put_params = {
            "Bucket": self.bucket_name,
            "Key": storage_path,
            "Body": data,
        }

        if content_type:
            put_params["ContentType"] = content_type

        self.client.put_object(**put_params)

    def get_file_path(self, storage_path: str) -> Path | None:
        """
        Get local file path.

        For S3 storage, returns None as files are stored remotely.

        Args:
            storage_path: Storage path to the artifact

        Returns:
            None (S3 does not have local file paths)
        """
        return None
