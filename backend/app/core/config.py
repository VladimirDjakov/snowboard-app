"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    _root_dir = Path(__file__).parent.parent.parent.parent

    model_config = SettingsConfigDict(
        env_file=_root_dir.joinpath(".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql://user:password@localhost:5432/dbname"],
    )
    database_echo: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )

    # Redis
    redis_url: str = Field(
        ...,
        description="Redis connection URL",
        examples=["redis://localhost:6379/0"],
    )

    # Storage
    storage_backend: Literal["local", "s3"] = Field(
        default="local",
        description="Storage backend type",
    )
    storage_local_path: str = Field(
        default="runtime/storage",
        description="Local filesystem path for storage",
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        description="S3/MinIO endpoint URL",
    )
    s3_access_key_id: str | None = Field(
        default=None,
        description="S3 access key ID",
    )
    s3_secret_access_key: str | None = Field(
        default=None,
        description="S3 secret access key",
    )
    s3_bucket_name: str | None = Field(
        default=None,
        description="S3 bucket name",
    )
    s3_region: str = Field(
        default="ru-msk-1",
        description="S3 region",
    )
    s3_presigned_url_expiry: int = Field(
        default=3600,
        description="Presigned URL expiration time in seconds",
        ge=1,
    )

    # Triton
    triton_url: str = Field(
        default="http://localhost:8001",
        description="Triton Inference Server URL",
    )

    # API
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
        ge=1,
        le=65535,
    )
    api_cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log format (json or text)",
    )

    # Environment
    environment: Literal["development", "production"] = Field(
        default="development",
        description="Application environment",
    )

    def model_post_init(self, __context) -> None:
        """Validate settings after initialization."""

        if self.storage_backend == "s3":
            if not self.s3_endpoint_url:
                raise ValueError("s3_endpoint_url is required when storage_backend is 's3'")
            if not self.s3_access_key_id:
                raise ValueError("s3_access_key_id is required when storage_backend is 's3'")
            if not self.s3_secret_access_key:
                raise ValueError("s3_secret_access_key is required when storage_backend is 's3'")
            if not self.s3_bucket_name:
                raise ValueError("s3_bucket_name is required when storage_backend is 's3'")


# Global settings instance
settings = Settings()
