"""Runtime singletons for composition."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.app.infrastructure.db.session import (
    create_engine_from_settings,
    create_session_factory,
)
from backend.app.infrastructure.storage import BaseStorage, create_storage_backend
from backend.app.presentation.bootstrap.settings import load_settings

_engine: Engine | None = None
_session_factory: Callable[[], Session] | None = None
_storage_instance: BaseStorage | None = None


def get_engine() -> Engine:
    """Get or create a shared SQLAlchemy engine."""
    global _engine

    if _engine is None:
        settings = load_settings()
        _engine = create_engine_from_settings(settings)

    return _engine


def get_session_factory() -> Callable[[], Session]:
    """Get or create a shared session factory."""
    global _session_factory

    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())

    return _session_factory


def get_session() -> Session:
    """Create a new database session."""
    return get_session_factory()()


def dispose_engine() -> None:
    """Dispose the shared engine (useful in tests or shutdown hooks)."""
    global _engine

    if _engine is not None:
        _engine.dispose()
        _engine = None


def get_storage() -> BaseStorage:
    """Get storage backend singleton."""
    global _storage_instance

    if _storage_instance is None:
        settings = load_settings()
        _storage_instance = create_storage_backend(settings)

    return _storage_instance
