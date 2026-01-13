"""Port for clock/time operations."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Interface for clock/time operations."""

    def now(self) -> datetime:
        """
        Get current time.

        Returns:
            Current datetime
        """
        ...
