"""PostgreSQL database session configuration."""

from collections.abc import Callable, Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.composition.settings import Settings

# Create declarative base for models
Base = declarative_base()


def create_engine_from_settings(settings: Settings) -> Engine:
    """
    Create SQLAlchemy engine from settings.

    Args:
        settings: Application settings

    Returns:
        SQLAlchemy engine instance
    """
    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,  # Verify connections before using them
        pool_size=5,
        max_overflow=10,
    )


def create_sessionmaker_from_engine(engine: Engine) -> Callable[[], Session]:
    """
    Create session factory from engine.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Session factory (callable that returns Session)
    """
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def get_db(session_factory: Callable[[], Session]) -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.

    Args:
        session_factory: Session factory callable

    Yields:
        Database session
    """
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
