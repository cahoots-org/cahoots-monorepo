FROM python:3.11

WORKDIR /app

# Copy the entire packages directory
COPY packages/ /app/packages/

# Install dependencies
RUN pip install --no-cache-dir psutil \
    && pip install --no-cache-dir -e /app/packages/core \
    && pip install --no-cache-dir -e /app/packages/events \
    && pip install --no-cache-dir -e /app/packages/context \
    && cd /app/packages/service && pip install -e .

# Set environment variables
ENV PYTHONPATH=/app/packages/service/src

# Run the service
CMD ["python", "-m", "cahoots_service.api.main"] 