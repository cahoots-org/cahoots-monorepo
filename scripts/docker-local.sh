#!/bin/bash

# Build the Docker image
docker build -t ai-dev-team:local .

# Run the container
docker run -p 8000:8000 \
    --env-file .env.local \
    -e ENV=local \
    ai-dev-team:local 