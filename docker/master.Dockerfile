FROM python:3.11-slim

WORKDIR /app

# Install redis-cli
RUN apt-get update && \
    apt-get install -y redis-tools && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir structlog

# Copy source code
COPY src/ src/
COPY config/ config/

# Set environment variables
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config/default.yaml
ENV AGENT_TYPE=master

# Expose port
EXPOSE 8000

# Run the service
CMD ["python", "-m", "src.agents.factory"] 