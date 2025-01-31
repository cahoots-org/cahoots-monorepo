#!/bin/bash

# Create buildkitd.toml with cache settings
echo "Creating buildkitd.toml configuration..."
cat > buildkitd.toml << EOL
[worker.oci]
  max-parallelism = 4

[worker.containerd]
  gc = true
  gc-keepstorage = 20000

[registry."docker.io"]
  mirrors = ["mirror.gcr.io"]

[registry."ghcr.io"]
  mirrors = ["mirror.gcr.io"]
EOL

# Create a new builder instance with larger cache
echo "Creating BuildKit builder..."
docker buildx create --use --name cahoots-builder \
  --driver docker-container \
  --driver-opt network=host \
  --buildkitd-flags '--allow-insecure-entitlement network.host' \
  --config ./buildkitd.toml

# Create cache directory
echo "Creating cache directory..."
mkdir -p /tmp/.buildx-cache

echo "BuildKit builder 'cahoots-builder' has been created and configured." 