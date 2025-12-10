#!/bin/bash
# Build and push test runner images to GCR
#
# Usage: ./build-images.sh <GCP_PROJECT_ID>
#
# Prerequisites:
# - gcloud CLI configured
# - Docker logged in to GCR: gcloud auth configure-docker

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <GCP_PROJECT_ID>"
    exit 1
fi

GCP_PROJECT_ID=$1
SCRIPT_DIR=$(dirname "$0")

echo "Building test runner images for project: $GCP_PROJECT_ID"

# Build Node.js runner
echo "Building Node.js runner..."
docker build --platform linux/amd64 \
    -t gcr.io/$GCP_PROJECT_ID/cahoots-runner-node:20 \
    -f $SCRIPT_DIR/Dockerfile.node \
    $SCRIPT_DIR

# Build Python runner
echo "Building Python runner..."
docker build --platform linux/amd64 \
    -t gcr.io/$GCP_PROJECT_ID/cahoots-runner-python:3.11 \
    -f $SCRIPT_DIR/Dockerfile.python \
    $SCRIPT_DIR

echo ""
echo "Images built successfully!"
echo ""
echo "To push to GCR, run:"
echo "  docker push gcr.io/$GCP_PROJECT_ID/cahoots-runner-node:20"
echo "  docker push gcr.io/$GCP_PROJECT_ID/cahoots-runner-python:3.11"
