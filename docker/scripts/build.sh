#!/bin/bash
set -euo pipefail

# Default values
REGISTRY=${REGISTRY:-"ghcr.io/your-org"}
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

# Build base image first
build_base() {
    log "Building base image..."
    docker build \
        --build-arg BUILDKIT_PROGRESS=$BUILDKIT_PROGRESS \
        --cache-from $REGISTRY/ai-dev-team-base:cache \
        --cache-from $REGISTRY/ai-dev-team-base:$TAG \
        -t $REGISTRY/ai-dev-team-base:$TAG \
        -t $REGISTRY/ai-dev-team-base:cache \
        -f docker/base/Dockerfile .
}

# Build agent image
build_agent() {
    local agent_name=$1
    log "Building agent image: $agent_name..."
    
    # Generate agent Dockerfile if it doesn't exist
    if [ ! -f "docker/agents/${agent_name}.Dockerfile" ]; then
        python docker/scripts/generate_agent_dockerfile.py "$agent_name"
    fi
    
    docker build \
        --build-arg BUILDKIT_PROGRESS=$BUILDKIT_PROGRESS \
        --build-arg BASE_IMAGE=$REGISTRY/ai-dev-team-base:$TAG \
        --cache-from $REGISTRY/ai-dev-team-agent-${agent_name}:cache \
        --cache-from $REGISTRY/ai-dev-team-agent-${agent_name}:$TAG \
        -t $REGISTRY/ai-dev-team-agent-${agent_name}:$TAG \
        -t $REGISTRY/ai-dev-team-agent-${agent_name}:cache \
        -f docker/agents/${agent_name}.Dockerfile .
}

# Main build process
main() {
    # Ensure we're in the project root
    if [ ! -f "pyproject.toml" ]; then
        error "Must run from project root"
    fi
    
    # Build base image first
    build_base
    
    # Build all agent images
    for config in config/agents/*.yaml; do
        agent_name=$(basename "$config" .yaml)
        build_agent "$agent_name"
    done
    
    log "All builds completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
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