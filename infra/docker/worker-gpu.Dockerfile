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
COPY workers/pyproject.toml workers/uv.lock* workers/pyproject.toml* ./

# Install Python dependencies
RUN uv pip install --system -e .

# Copy workers code
COPY workers/ ./workers/
COPY contracts/ ./contracts/
COPY rules/ ./rules/
COPY schemas/ ./schemas/

# Set Python path
ENV PYTHONPATH=/app

# Run RQ worker for GPU queue
CMD ["sh", "-c", "rq worker --url ${REDIS_URL:-redis://redis:6379/0} gpu"]

