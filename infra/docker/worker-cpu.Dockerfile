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
COPY workers/pyproject.toml workers/uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -e .


# Copy workers code
COPY workers/ ./workers/
COPY contracts/ ./contracts/
COPY rules/ ./rules/
COPY schemas/ ./schemas/

# Set Python path
ENV PYTHONPATH=/app

# Run RQ worker for CPU queue
CMD ["sh", "-c", "rq worker --url ${REDIS_URL:-redis://redis:6379/0} cpu"]

