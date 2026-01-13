"""Tests for backend logging."""

import logging

from backend.app.infrastructure.logging import setup_logging
from backend.app.presentation.bootstrap.settings import Settings


def test_logging_setup_json_format():
    """Test logging setup with JSON format."""
    settings = Settings()
    setup_logging(settings)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO

    # Check that handler is configured
    assert len(root_logger.handlers) > 0
    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)

    # Check formatter
    formatter = handler.formatter
    assert formatter is not None


def test_logging_setup_text_format():
    """Test logging setup with text format."""
    settings = Settings(
        log_format="text",
    )
    setup_logging(settings)

    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    formatter = handler.formatter

    # Text formatter should be standard Formatter
    assert isinstance(formatter, logging.Formatter)


def test_logging_levels():
    """Test that different log levels work correctly."""

    settings = Settings(
        log_level="DEBUG",
    )
    setup_logging(settings)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_logging_context_fields():
    """Test that context fields are added to log records."""
    settings = Settings()
    setup_logging(settings)

    _ = logging.getLogger("test")

    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Apply filters
    for handler in logging.getLogger().handlers:
        for filter_obj in handler.filters:
            filter_obj.filter(record)

    # Check context fields
    assert hasattr(record, "service")
    assert record.service == "backend"
    assert hasattr(record, "environment")
    assert record.environment == settings.environment


def test_logging_third_party_loggers():
    """Test that third-party loggers are configured."""
    settings = Settings()
    setup_logging(settings)

    # Check uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    assert uvicorn_logger.level == logging.INFO

    # Check fastapi logger
    fastapi_logger = logging.getLogger("fastapi")
    assert fastapi_logger.level == logging.INFO
