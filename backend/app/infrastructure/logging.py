"""Structured logging configuration for backend."""

import logging
import sys

from pythonjsonlogger import json

from backend.app.composition.settings import Settings


class BackendContextFilter(logging.Filter):
    """Logging filter to add backend context fields."""

    def __init__(self, environment: str) -> None:
        """Initialize filter with environment.

        Args:
            environment: Application environment.
        """
        super().__init__()
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to log record."""
        record.service = "backend"
        record.environment = self.environment
        return True


def setup_logging(config: Settings) -> None:
    """Configure structured logging for the application.

    Args:
        config: Application settings containing logging configuration.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.log_level))

    # Add context filter
    context_filter = BackendContextFilter(config.environment)
    console_handler.addFilter(context_filter)

    # Set formatter based on log format
    if config.log_format == "json":
        formatter = json.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            timestamp=True,
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(config.log_level)
    logging.getLogger("uvicorn.access").setLevel(
        "INFO" if config.environment == "production" else "DEBUG"
    )
    logging.getLogger("fastapi").setLevel(config.log_level)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("httpcore").setLevel("WARNING")
