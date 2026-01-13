"""Health check endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Liveness probe.

    Returns:
        Simple status indicating the service is alive
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(request: Request):
    """
    Readiness probe - checks database, Redis, storage.

    Checks the health of all critical dependencies:
    - Database connection
    - Redis connection
    - Storage backend

    Returns:
        Detailed status of all components with appropriate HTTP status code
    """
    # Get container from app state
    container = request.app.state.container

    # Check each component
    db_healthy = container.check_database_health()
    redis_healthy = container.check_redis_health()
    storage_healthy = container.check_storage_health()

    # Overall status
    all_healthy = db_healthy and redis_healthy and storage_healthy

    status_code = 200 if all_healthy else 503

    response_data = {
        "status": "ready" if all_healthy else "not_ready",
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "storage": "healthy" if storage_healthy else "unhealthy",
        },
    }

    return JSONResponse(content=response_data, status_code=status_code)
