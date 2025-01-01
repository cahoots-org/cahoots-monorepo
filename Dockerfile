FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies and security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy application code
COPY . .

# Set ownership and permissions
RUN chown -R appuser:appuser /app \
    && chmod -R 550 /app \
    && chmod -R 770 /app/logs \
    && chmod -R 770 /app/tmp

# Switch to non-root user
USER appuser

# Health check with proper timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set resource limits
ENV WORKERS=4 \
    WORKER_CLASS=uvicorn.workers.UvicornWorker \
    TIMEOUT=120 \
    KEEP_ALIVE=120 \
    MAX_REQUESTS=10000 \
    MAX_REQUESTS_JITTER=1000

# Start application with proper worker configuration and resource limits
CMD ["sh", "-c", "python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS} \
    --worker-class ${WORKER_CLASS} \
    --timeout ${TIMEOUT} \
    --keep-alive ${KEEP_ALIVE} \
    --limit-max-requests ${MAX_REQUESTS} \
    --limit-max-requests-jitter ${MAX_REQUESTS_JITTER} \
    --no-access-log \
    --proxy-headers"] 