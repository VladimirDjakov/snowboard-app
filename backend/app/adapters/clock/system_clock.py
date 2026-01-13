"""System clock adapter."""

from datetime import UTC, datetime


class SystemClock:
    """System clock implementation of Clock port."""

    def now(self) -> datetime:
        """Get current time."""
        return datetime.now(UTC)
