FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Python 3.12
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-distutils \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python and pip
RUN ln -s /usr/bin/python3.12 /usr/bin/python && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

WORKDIR /app

# Install uv for faster package management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -e ".[workers-gpu]"

# Copy backend (includes workers)
COPY backend/ ./backend/
COPY contracts/ ./contracts/
COPY rules/ ./rules/
COPY schemas/ ./schemas/

# Set Python path
ENV PYTHONPATH=/app

# Run RQ worker via application entrypoint (GPU queue)
CMD ["sh", "-c", "python -m backend.app.presentation.workers.rq.worker_entrypoint gpu"]
