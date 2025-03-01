FROM python:3.11-slim as builder

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir pip setuptools wheel build

COPY pyproject.toml requirements.txt ./

COPY services/api ./services/api
COPY libs/core ./libs/core
COPY libs/events ./libs/events
COPY libs/context ./libs/context

# Install packages in dependency order - events has no dependency on context
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    pip install -e ./libs/core && \
    pip install -e ./libs/events && \
    pip install -e ./libs/context && \
    pip install -e ./services/api

FROM python:3.11-slim

WORKDIR /app

RUN echo "deb http://cloudfront.debian.net/debian bookworm main" > /etc/apt/sources.list && \
    for i in $(seq 1 3); do \
        apt-get update && \
        apt-get install -y curl iputils-ping dnsutils && \
        break || \
        if [ $i -lt 3 ]; then \
            sleep 5; \
        else \
            exit 1; \
        fi \
    done

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY services/api/cahoots_service /app/cahoots_service

CMD ["uvicorn", "cahoots_service.main:app", "--host", "0.0.0.0", "--port", "8000"]