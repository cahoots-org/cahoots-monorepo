#!/bin/bash

set -e

# Set variables
NAMESPACE="cahoots"
MAIN_APP="cahoots"
SERVICES=("master" "project-manager" "developer" "ux-designer" "tester")

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE 2>/dev/null || true

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check required environment variables
if [ -z "$GITHUB_API_KEY" ]; then
    echo "Error: GITHUB_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$TOGETHER_API_KEY" ]; then
    echo "Error: TOGETHER_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY environment variable is required"
    exit 1
fi

# Build Docker images for all services
for SERVICE in "${SERVICES[@]}"; do
    echo "Building Docker image for $SERVICE..."
    docker build -t "$MAIN_APP-$SERVICE:latest" -f "docker/$SERVICE.Dockerfile" .
done

# Create a temporary directory for processed Kubernetes files
TEMP_DIR=$(mktemp -d)
cp -r k8s/* "$TEMP_DIR/"

# Process the secrets file with environment variables
SECRETS_FILE="$TEMP_DIR/overlays/development/secrets.yaml"
CONFIG_FILE="$TEMP_DIR/overlays/development/patches/configmap.yaml"

# Function to replace environment variables in a file
replace_env_vars() {
    local file=$1
    sed -i '' "s|\${GITHUB_API_KEY}|$GITHUB_API_KEY|g" "$file"
    sed -i '' "s|\${TOGETHER_API_KEY}|$TOGETHER_API_KEY|g" "$file"
    sed -i '' "s|\${API_KEY}|$API_KEY|g" "$file"
    sed -i '' "s|\${REDIS_PASSWORD}|dev-password-123|g" "$file"
    sed -i '' "s|\${JWT_SECRET_KEY}|dev-jwt-secret-key-123|g" "$file"
    sed -i '' "s|\${TRELLO_API_KEY}|dev-trello-api-key-123|g" "$file"
    sed -i '' "s|\${TRELLO_API_SECRET}|dev-trello-api-secret-123|g" "$file"
}

# Replace environment variables in both files
replace_env_vars "$SECRETS_FILE"
replace_env_vars "$CONFIG_FILE"

# Apply Kustomize configuration using the processed files
kubectl apply -k "$TEMP_DIR/overlays/development"

# Clean up temporary directory
rm -rf "$TEMP_DIR"

echo "Waiting for services to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=cahoots -n $NAMESPACE --timeout=300s

echo "Services deployed successfully!"
echo "You can access the API at http://localhost:80"
echo "To view logs, run: kubectl logs -f deployment/$MAIN_APP-master -n $NAMESPACE"
echo "To access the Kubernetes dashboard, run: kubectl proxy" 