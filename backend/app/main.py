"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import files, health, videos
from backend.app.composition.container import Container
from backend.app.composition.settings import load_settings

# Load settings
settings = load_settings()

# Create container
container = Container(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: store container in app state for health checks
    app.state.container = container
    yield
    # Shutdown
    container.close()


app = FastAPI(
    title="Snowboard Coach API",
    description="API for snowboard video analysis pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(videos.router, prefix="/v1/videos", tags=["videos"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
