# syntax=docker/dockerfile:1.4

# Build stage for compiling dependencies
FROM python:3.11-slim AS builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG PIP_NO_CACHE_DIR=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies with retry logic and cleanup
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    for i in $(seq 1 3); do \
        apt-get update -y && \
        apt-get install -y --no-install-recommends \
            build-essential \
            git \
            && apt-get clean \
            && rm -rf /var/lib/apt/lists/* \
            && break || sleep 1; \
    done

WORKDIR /build

# Install build tools with version pinning
RUN pip install --no-cache-dir \
    pip==23.3.1 \
    setuptools==69.0.2 \
    wheel==0.41.2 \
    hatchling==1.18.0

# Copy dependency files for better layer caching
COPY pyproject.toml requirements.txt ./
COPY libs/core/pyproject.toml libs/core/
COPY libs/events/pyproject.toml libs/events/
COPY libs/context/pyproject.toml libs/context/
COPY services/*/pyproject.toml services/

# Install dependencies in a single layer with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    find /build -name pyproject.toml -exec pip install -e {} \;

# Development image
FROM builder AS dev

# Copy installed packages and binaries
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install development tools with version pinning
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    uvicorn[standard]==0.24.0 \
    watchfiles==0.21.0 \
    pytest==7.4.3 \
    pytest-cov==4.1.0 \
    black==23.12.1 \
    isort==5.13.2 \
    mypy==1.7.1

# Set development environment
ENV PYTHONPATH=/app \
    CONFIG_PATH=/app/config \
    LOG_LEVEL=DEBUG \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Production image
FROM python:3.11-slim AS prod

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd -m -s /bin/bash app && \
    mkdir -p /app/config && \
    chown -R app:app /app

WORKDIR /app
USER app

# Set production environment
ENV PYTHONPATH=/app \
    CONFIG_PATH=/app/config \
    LOG_LEVEL=INFO \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy application code
COPY --chown=app:app . .

# Install the application in development mode
RUN pip install -e .

# Validation step - now after installing the application
RUN pip list | grep -i cahoots || echo "Warning: No cahoots packages found"

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command
CMD ["python", "-m", "cahoots"] 