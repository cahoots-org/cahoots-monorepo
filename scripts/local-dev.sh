#!/bin/bash

# Set error handling
set -e

# Source environment variables if they exist
if [ -f .env ]; then
    source .env
fi

# Setup BuildKit if not already set up
if ! docker buildx ls | grep -q "cahoots-builder"; then
    ./scripts/setup-buildkit.sh
fi

# Clean up old resources
./scripts/cleanup.sh

# Build base image with BuildKit
echo "Building base image..."
docker buildx build \
  --builder cahoots-builder \
  --cache-from type=local,src=/tmp/.buildx-cache \
  --cache-to type=local,dest=/tmp/.buildx-cache \
  --load \
  -t cahoots-base:latest \
  -f docker/base/Dockerfile \
  .

# Build agent images
for agent in developer tester ux-designer project-manager context-manager; do
  echo "Building $agent agent..."
  docker buildx build \
    --builder cahoots-builder \
    --cache-from type=local,src=/tmp/.buildx-cache \
    --cache-to type=local,dest=/tmp/.buildx-cache \
    --build-arg BASE_IMAGE=cahoots-base:latest \
    --load \
    -t "cahoots-${agent}:latest" \
    -f "docker/agents/${agent}.Dockerfile" \
    .
done

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl delete -f k8s/local/02-agents.yaml || true
kubectl apply -f k8s/local/00-namespace.yaml
kubectl apply -f k8s/local/01-redis.yaml
kubectl apply -f k8s/local/02-agents.yaml

echo "Waiting for pods to be ready..."
kubectl wait --namespace cahoots \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/part-of=cahoots \
  --timeout=300s

echo "Development environment is ready!" 