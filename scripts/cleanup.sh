#!/bin/bash

# Stop all running containers
echo "Stopping all running containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all containers
echo "Removing all containers..."
docker rm $(docker ps -aq) 2>/dev/null || true

# Remove all cahoots images
echo "Removing all cahoots images..."
docker rmi $(docker images | grep 'cahoots' | awk '{print $3}') 2>/dev/null || true

# Clean up BuildKit cache
echo "Cleaning up BuildKit cache..."
rm -rf /tmp/.buildx-cache/*

# Prune Docker system
echo "Pruning Docker system..."
docker system prune -f

echo "Cleanup complete!" 