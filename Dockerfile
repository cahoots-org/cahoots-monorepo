FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with retry logic
RUN for i in $(seq 1 3); do \
        apt-get update -y && \
        apt-get install -y --no-install-recommends \
            curl \
        && rm -rf /var/lib/apt/lists/* && break \
        || if [ $i -lt 3 ]; then sleep 5; else false; fi; \
    done

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 