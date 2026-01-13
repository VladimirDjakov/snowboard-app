"""Port for Unit of Work pattern."""

from typing import Protocol


class UnitOfWork(Protocol):
    """Interface for Unit of Work pattern."""

    def commit(self) -> None:
        """Commit current transaction."""
        ...

    def rollback(self) -> None:
        """Rollback current transaction."""
        ...

    def __enter__(self) -> "UnitOfWork":
        """Enter context manager."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        ...
