#!/bin/bash
set -e

# Configuration
REGISTRY=${REGISTRY:-localhost}
BASE_IMAGE=${BASE_IMAGE:-cahoots-base:latest}
BUILD_ARGS="--platform=linux/amd64 --load"

# Build type can be 'dev' or 'prod'
BUILD_TYPE=${BUILD_TYPE:-dev}

# Enable buildkit for better performance
export DOCKER_BUILDKIT=1

# Function to build an image
build_image() {
    local dockerfile=$1
    local tag=$2
    local target=${3:-$BUILD_TYPE}
    
    echo "Building $tag from $dockerfile with target $target..."
    docker build $BUILD_ARGS \
        --target $target \
        --cache-from type=local,src=/tmp/.buildx-cache \
        --cache-to type=local,dest=/tmp/.buildx-cache \
        -t $REGISTRY/$tag \
        -f $dockerfile .
}

# Clean function
clean() {
    echo "Cleaning up..."
    docker system prune -f
    rm -rf /tmp/.buildx-cache
}

# Main build function
main() {
    local cmd=${1:-all}
    
    case $cmd in
        clean)
            clean
            ;;
        base)
            build_image docker/base/Dockerfile $BASE_IMAGE
            ;;
        services)
            build_image docker/services/context-manager.Dockerfile cahoots-context-manager:latest
            ;;
        agents)
            for agent in developer project-manager tester ux-designer; do
                build_image docker/agents/$agent.Dockerfile cahoots-$agent:latest
            done
            ;;
        all)
            main base
            main services
            main agents
            ;;
        *)
            echo "Unknown command: $cmd"
            echo "Usage: $0 {clean|base|services|agents|all}"
            exit 1
            ;;
    esac
}

main "$@" 