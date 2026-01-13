"""PostgreSQL implementation of Unit of Work."""

from sqlalchemy.orm import Session


class PostgresUnitOfWork:
    """PostgreSQL implementation of Unit of Work."""

    def __init__(self, session: Session) -> None:
        """
        Initialize Unit of Work with session.

        Args:
            session: SQLAlchemy session
        """
        self._session = session
        self._committed = False

    @property
    def session(self) -> Session:
        """Get current database session."""
        return self._session

    def commit(self) -> None:
        """Commit current transaction."""
        self._session.commit()
        self._committed = True

    def rollback(self) -> None:
        """Rollback current transaction."""
        self._session.rollback()

    def __enter__(self) -> "PostgresUnitOfWork":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type is not None:
            # Exception occurred, rollback
            self.rollback()
        elif not self._committed:
            # No exception but not explicitly committed, rollback
            self.rollback()
        # If committed, do nothing (session will be closed by caller)
