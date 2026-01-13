"""FastAPI dependencies for API layer (session + use cases)."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.application.ports.storage import Storage
from backend.app.composition.container import Container, UseCases


def get_container(request: Request) -> Container:
    """Get container from app state."""

    return request.app.state.container


def get_use_cases(request: Request) -> Generator[UseCases, None, None]:
    """Build request-scoped use cases and manage DB session lifecycle."""

    container = get_container(request)
    session: Session = container.get_session()
    try:
        yield container.build_use_cases(session)
    finally:
        session.close()


def get_storage(request: Request) -> Storage:
    """Get storage port from container (no DB session required)."""

    return get_container(request).storage
