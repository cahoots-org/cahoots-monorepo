#!/bin/bash
set -e

# Install required Python packages if not present
pip install PyJWT requests cryptography

# Generate the token
TOKEN=$(python3 scripts/generate_github_token.py)

if [ -z "$TOKEN" ]; then
    echo "Failed to generate token"
    exit 1
fi

# Create or update the secret
kubectl create secret docker-registry ghcr-pull-secret \
    --namespace=cahoots \
    --docker-server=ghcr.io \
    --docker-username="cahoots-package-reader[bot]" \
    --docker-password="$TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "Secret updated successfully" 