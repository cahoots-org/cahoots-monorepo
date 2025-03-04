#!/bin/bash
set -euo pipefail

# Default values
REGISTRY=${REGISTRY:-"ghcr.io"}
IMAGE_PREFIX=${IMAGE_PREFIX:-"cahoots-org"}
TAG=${TAG:-"latest"}
BUILDKIT_PROGRESS=${BUILDKIT_PROGRESS:-"auto"}
DOCKER_BUILDKIT=1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
log() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Build master image
build_master() {
    log "Building master image..."
    DOCKER_BUILDKIT=1 docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -f docker/master/Dockerfile \
        --cache-from $REGISTRY/$IMAGE_PREFIX/cahoots-master:cache \
        --cache-from $REGISTRY/$IMAGE_PREFIX/cahoots-master:$TAG \
        -t $REGISTRY/$IMAGE_PREFIX/cahoots-master:$TAG \
        -t $REGISTRY/$IMAGE_PREFIX/cahoots-master:cache \
        .
}

# Build web-client image
build_web_client() {
    log "Building web-client image..."
    DOCKER_BUILDKIT=1 docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -f docker/web-client/Dockerfile \
        --cache-from $REGISTRY/$IMAGE_PREFIX/cahoots-web-client:cache \
        --cache-from $REGISTRY/$IMAGE_PREFIX/cahoots-web-client:$TAG \
        -t $REGISTRY/$IMAGE_PREFIX/cahoots-web-client:$TAG \
        -t $REGISTRY/$IMAGE_PREFIX/cahoots-web-client:cache \
        .
}

# Main build process
main() {
    # Ensure we're in the project root
    if [ ! -f "pyproject.toml" ]; then
        error "Must run from project root"
    fi
    
    # Build images
    build_master
    build_web_client
    
    log "All builds completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --prefix)
            IMAGE_PREFIX="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --progress)
            BUILDKIT_PROGRESS="$2"
            shift 2
            ;;
        *)
            error "Unknown argument: $1"
            ;;
    esac
done

# Run main build process
main 