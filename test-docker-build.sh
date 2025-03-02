#!/bin/bash
# Script to test Docker build and push locally

# Default values
SERVICE="base"
PUSH=false
REGISTRY="ghcr.io"
OWNER=$(git config --get user.username || echo "local")
REPO="cahoots"
TAG="test"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --service|-s)
            SERVICE="$2"
            shift
            shift
            ;;
        --push|-p)
            PUSH=true
            shift
            ;;
        --registry|-r)
            REGISTRY="$2"
            shift
            shift
            ;;
        --owner|-o)
            OWNER="$2"
            shift
            shift
            ;;
        --repo)
            REPO="$2"
            shift
            shift
            ;;
        --tag|-t)
            TAG="$2"
            shift
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -s, --service SERVICE    Service to build (default: base)"
            echo "  -p, --push              Push the image to registry"
            echo "  -r, --registry REGISTRY  Docker registry (default: ghcr.io)"
            echo "  -o, --owner OWNER        Owner/organization (default: git username or 'local')"
            echo "  -t, --tag TAG            Image tag (default: test)"
            echo "      --repo REPO          Repository name (default: cahoots)"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Determine Dockerfile path
if [ "$SERVICE" = "base" ]; then
    DOCKERFILE="docker/base/Dockerfile"
elif [ "$SERVICE" = "master" ]; then
    DOCKERFILE="docker/master/Dockerfile"
elif [ "$SERVICE" = "context_manager" ]; then
    DOCKERFILE="docker/services/context-manager.Dockerfile"
else
    DOCKERFILE="docker/agent/Dockerfile"
fi

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo "Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

# Build the image
IMAGE_NAME="$REGISTRY/$OWNER/$REPO-$SERVICE:$TAG"
echo "Building image: $IMAGE_NAME"
echo "Using Dockerfile: $DOCKERFILE"

docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" .
BUILD_RESULT=$?

if [ $BUILD_RESULT -ne 0 ]; then
    echo "Error: Docker build failed"
    exit 1
fi

echo "Build successful!"

# Push the image if requested
if [ "$PUSH" = true ]; then
    echo "Pushing image: $IMAGE_NAME"
    
    # Check if logged in to registry
    if ! docker info | grep -q "$REGISTRY"; then
        echo "Not logged in to $REGISTRY. Please login first with:"
        echo "  docker login $REGISTRY"
        exit 1
    fi
    
    docker push "$IMAGE_NAME"
    PUSH_RESULT=$?
    
    if [ $PUSH_RESULT -ne 0 ]; then
        echo "Error: Docker push failed"
        exit 1
    fi
    
    echo "Push successful!"
fi 