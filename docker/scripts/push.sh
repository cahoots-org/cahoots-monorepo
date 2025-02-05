#!/bin/bash
set -euo pipefail

# Default values
REGISTRY=${REGISTRY:-"ghcr.io/cahoots-org"}
TAG=${TAG:-"latest"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
log() {
    echo -e "${GREEN}[PUSH]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Push base image
push_base() {
    log "Pushing base image..."
    docker push $REGISTRY/cahoots-monorepo-base:$TAG
    docker push $REGISTRY/cahoots-monorepo-base:cache
}

# Push agent image
push_agent() {
    local agent_name=$1
    log "Pushing agent image: $agent_name..."
    docker push $REGISTRY/cahoots-monorepo-agent-${agent_name}:$TAG
    docker push $REGISTRY/cahoots-monorepo-agent-${agent_name}:cache
}

# Main push process
main() {
    # Push base image first
    push_base

    # Push all agent images
    for config in config/agents/*.yaml; do
        agent_name=$(basename "$config" .yaml)
        push_agent "$agent_name"
    done
    
    log "All images pushed successfully!"
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
        *)
            error "Unknown argument: $1"
            ;;
    esac
done

# Run main push process
main 