# Build stage for core dependencies
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime as builder

WORKDIR /app

# Configure apt for better reliability
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/10no-check-valid-until && \
    echo 'Acquire::Check-Date "false";' > /etc/apt/apt.conf.d/10no-check-date

# Install build dependencies with retry logic
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    for i in $(seq 1 3); do \
        (apt-get update -y && \
         apt-get install -y --no-install-recommends \
            build-essential \
            curl \
        ) && break || if [ $i -lt 3 ]; then sleep 5; else exit 1; fi; \
    done

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install dependencies using pip cache
COPY requirements-core.txt requirements-ml.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-core.txt && \
    pip install -r requirements-ml.txt

# Final stage
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /opt/conda/lib/python3.10/site-packages /opt/conda/lib/python3.10/site-packages
COPY --from=builder /opt/conda/bin /opt/conda/bin

# Copy only necessary application files
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV ENV=local

# Run the application with environment variables from .env file
CMD ["sh", "-c", "python -c 'from dotenv import load_dotenv; load_dotenv()' && uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"] 