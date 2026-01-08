"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe - checks database, Redis, storage."""
    # TODO: Implement actual checks for database, Redis, storage
    return {"status": "ready"}
