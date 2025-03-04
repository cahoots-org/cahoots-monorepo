# Build stage
FROM python:3.11-slim as builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir pip setuptools wheel build

# Copy project files
COPY pyproject.toml requirements.txt ./
COPY services/api ./services/api
COPY libs/core ./libs/core
COPY libs/events ./libs/events
COPY libs/context ./libs/context

# Install dependencies and build packages in correct order
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    pip install -e ./libs/core && \
    pip install -e ./libs/events && \
    pip install -e ./libs/context && \
    pip install -e ./services/api

# Runtime stage
FROM python:3.11-slim

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Switch to a more reliable mirror and install runtime dependencies
RUN echo "deb http://cloudfront.debian.net/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://cloudfront.debian.net/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://cloudfront.debian.net/debian bookworm-updates main" >> /etc/apt/sources.list && \
    for i in {1..3}; do \
        (apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            curl \
            iputils-ping \
            dnsutils \
            postgresql-client && \
        rm -rf /var/lib/apt/lists/* && \
        break) || if [ $i -lt 3 ]; then sleep 5; fi; \
    done

# Copy installed packages and code from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /build/services/api /app/services/api
COPY --from=builder /build/libs/core /app/libs/core
COPY --from=builder /build/libs/events /app/libs/events
COPY --from=builder /build/libs/context /app/libs/context

# Create necessary directories
RUN mkdir -p /app/services /app/libs

# Copy startup script
COPY docker/master/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"] 