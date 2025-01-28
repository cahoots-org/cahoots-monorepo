#!/bin/bash
set -e

# Build Docker images
echo "Building Docker images..."
services=("master" "developer" "project-manager" "tester" "ux-designer" "context-manager")

for service in "${services[@]}"; do
    echo "Building ${service}..."
    # Convert any remaining underscores to hyphens in the Dockerfile path
    dockerfile_path="docker/${service//-/_}/Dockerfile"
    # Build with the correct image name format that Kubernetes expects
    docker build -t "cahoots-${service}:latest" -f "$dockerfile_path" .
done

echo "All images built successfully!"
echo "You can now run ./k8s/base/scripts/run_local.sh to deploy" 