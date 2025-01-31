# Build from base development image for local development
ARG BASE_IMAGE=localhost/cahoots-base:latest
FROM ${BASE_IMAGE} AS dev

# Service configuration
ENV SERVICE_NAME=context-manager \
    SERVICE_DESCRIPTION="Context Manager Service for Cahoots" \
    CONFIG_PATH=/etc/cahoots/context-manager \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app/services/context-manager/src

# Install development dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    watchfiles

# Set up development environment
WORKDIR /app/services/context-manager
VOLUME ["/app/services/context-manager"]

# Development command with hot reload
CMD ["uvicorn", "cahoots_context_manager.service:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/services/context-manager/src"]

# Production build
FROM ${BASE_IMAGE} AS prod

# Copy only the service code
COPY services/context-manager /app/services/context-manager

# Production command
CMD ["python", "-m", "cahoots_context_manager.service"] 