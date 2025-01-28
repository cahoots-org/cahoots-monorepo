FROM python:3.11-slim

WORKDIR /app

# Copy the entire packages directory
COPY packages/ /app/packages/

# Install dependencies
RUN pip install --no-cache-dir -e /app/packages/core \
    && pip install --no-cache-dir -e /app/packages/events \
    && pip install --no-cache-dir -e /app/packages/context \
    && pip install --no-cache-dir -e /app/packages/service \
    && pip install --no-cache-dir -e /app/packages/agents

# Set environment variables
ENV PYTHONPATH=/app

# Run the context manager service
CMD ["python", "-m", "packages.agents.src.cahoots_agents.context_manager.main"] 