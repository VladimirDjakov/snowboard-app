"""Application-level DTOs for use case outputs (presentation-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class StageView:
    """Ordered stage view for read models."""

    name: str
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
