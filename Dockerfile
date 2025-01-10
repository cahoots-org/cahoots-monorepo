FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Configure package repositories and install build dependencies
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    for i in $(seq 1 3); do \
        (apt-get update -y && \
        apt-get install -y --no-install-recommends \
            build-essential \
            curl && \
        break) || \
        if [ $i -lt 3 ]; then \
            sleep 5; \
        else \
            false; \
        fi; \
    done && \
    rm -rf /var/lib/apt/lists/*

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

# Configure package repositories and install runtime dependencies
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    for i in $(seq 1 3); do \
        (apt-get update -y && \
        apt-get upgrade -y && \
        apt-get install -y --no-install-recommends \
            curl \
            ca-certificates && \
        break) || \
        if [ $i -lt 3 ]; then \
            sleep 5; \
        else \
            false; \
        fi; \
    done && \
    rm -rf /var/lib/apt/lists/* && \
    update-ca-certificates

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 550 /app && \
    chmod -R 770 /app/logs && \
    chmod -R 770 /app/tmp

# Switch to non-root user
USER appuser

# Health check with proper timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set resource limits
ENV WORKERS=4 \
    TIMEOUT_KEEP_ALIVE=120 \
    MAX_REQUESTS=10000 \
    MAX_REQUESTS_JITTER=1000

# Start application with proper worker configuration and resource limits
CMD ["python", "-m", "uvicorn", "src.api.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "4", \
    "--timeout-keep-alive", "120", \
    "--proxy-headers"] 