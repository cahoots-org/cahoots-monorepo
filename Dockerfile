# Multi-stage build for Cahoots Monolith using uv
FROM python:3.11-slim@sha256:a0939570b38cddeb861b8e75d20b1c8218b21562b18f301171904b544e8cf228 AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set build arguments
ARG APP_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy project files
WORKDIR /app
COPY pyproject.toml .

# Install dependencies using uv with CPU-only PyTorch
RUN uv venv /opt/venv && \
    UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu \
    uv pip install --python /opt/venv/bin/python --no-cache -r pyproject.toml

# Production stage
FROM python:3.11-slim@sha256:a0939570b38cddeb861b8e75d20b1c8218b21562b18f301171904b544e8cf228

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Create app directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY .env.example .env

# Create cache directory for HuggingFace models
RUN mkdir -p /home/appuser/.cache/huggingface && \
    chown -R appuser:appuser /app /home/appuser

# Set environment variable for HuggingFace cache
ENV HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/transformers

# Switch to non-root user
USER appuser

# Expose port (Railway will use $PORT env var)
EXPOSE 8000

# Command to run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
