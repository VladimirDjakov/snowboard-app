"""Tests for backend configuration."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.presentation.bootstrap.settings import Settings


@pytest.fixture
def test_env_vars():
    """Set up test environment variables."""
    env_vars = {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    # Save original values
    original = {}
    for key, value in env_vars.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # Restore original values
    for key, original_value in original.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


def test_config_env_file():
    settings = Settings()
    env_file = settings.model_config["env_file"]
    assert Path(env_file).is_file()


def test_config_env_vars(test_env_vars):
    """Test that configuration loads from environment variables."""
    settings = Settings()

    assert settings.database_url == test_env_vars["DATABASE_URL"]
    assert settings.redis_url == test_env_vars["REDIS_URL"]


def test_config_defaults():
    """Test default values for optional settings."""
    settings = Settings()
    assert settings.database_echo is False
    assert settings.storage_local_path == "runtime/storage"
    assert settings.triton_url == "http://localhost:8001"
    assert settings.s3_region == "ru-msk-1"
    assert settings.s3_presigned_url_expiry == 3600


def test_config_s3_validation():
    """Test configuration with custom environment variables."""
    orig_storage_backend = os.environ.get("STORAGE_BACKEND")
    os.environ["STORAGE_BACKEND"] = "s3"

    with pytest.raises(ValidationError, match="s3_endpoint_url is required"):
        Settings()
    # Always clean up
    if orig_storage_backend is None:
        os.environ.pop("STORAGE_BACKEND", None)
    else:
        os.environ["STORAGE_BACKEND"] = orig_storage_backend


def test_config_s3_with_all_fields():
    """Test S3 configuration with all required fields."""

    settings = Settings(
        storage_backend="s3",
        s3_endpoint_url="http://localhost:9000",
        s3_access_key_id="test-key",
        s3_secret_access_key="test-secret",
        s3_bucket_name="test-bucket",
    )
    assert settings.storage_backend == "s3"
    assert settings.s3_endpoint_url == "http://localhost:9000"
    assert settings.s3_access_key_id == "test-key"
    assert settings.s3_secret_access_key == "test-secret"
    assert settings.s3_bucket_name == "test-bucket"
