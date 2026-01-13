"""PostgreSQL database session configuration."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

if TYPE_CHECKING:
    from backend.app.presentation.bootstrap.settings import Settings

# Create declarative base for models
Base = declarative_base()


def create_engine_from_settings(settings: "Settings") -> Engine:
    """
    Create SQLAlchemy engine from settings.

    Args:
        settings: Application settings

    Returns:
        SQLAlchemy engine instance
    """
    return create_engine(
        url=settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,  # Verify connections before using them
        pool_size=5,
        max_overflow=10,
    )


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """
    Create session factory from engine.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Session factory (callable that returns Session)
    """
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )
