FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including ffmpeg for video transcoding
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -e ".[workers-cpu]"


# Copy backend (includes workers)
COPY backend/ ./backend/
COPY contracts/ ./contracts/
COPY rules/ ./rules/
COPY schemas/ ./schemas/

# Set Python path
ENV PYTHONPATH=/app

# Run RQ worker via application entrypoint (CPU queue)
CMD ["sh", "-c", "python -m backend.app.presentation.workers.rq.worker_entrypoint cpu"]
