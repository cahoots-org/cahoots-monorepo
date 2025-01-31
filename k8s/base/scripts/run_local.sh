#!/bin/bash
set -e

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if kubectl is configured
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "Kubernetes is not running. Please start your local cluster first."
    exit 1
fi

# Create namespace if it doesn't exist
echo "Creating namespace..."
kubectl create namespace cahoots --dry-run=client -o yaml | kubectl apply -f -

# Build base image first
echo "Building base image..."
docker build -t cahoots-base:latest -f docker/base.Dockerfile .

# Build Docker images
echo "Building Docker images..."
services=("master" "developer" "project-manager" "tester" "ux-designer" "context-manager")
for service in "${services[@]}"; do
    if [ -f "docker/${service}/Dockerfile" ]; then
        echo "Building ${service} from docker/${service}/Dockerfile..."
        docker build -t "cahoots-${service}:latest" -f "docker/${service}/Dockerfile" .
    else
        echo "Warning: No Dockerfile found for ${service}"
        continue
    fi
done

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -k k8s/overlays/development

# Wait for deployments
echo "Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s deployment --all -n cahoots || {
    echo "Error: Some deployments failed to become ready. Check status with: kubectl get pods -n cahoots"
    exit 1
}

# Port forward the main service
echo "Setting up port forwarding..."
kubectl port-forward svc/cahoots-master 8000:80 -n cahoots &

echo "Deployment complete! Services are available at:"
echo "Main API: http://localhost:8000"
echo ""
echo "To view logs: kubectl logs -f deployment/cahoots-master -n cahoots"
echo "To check status: kubectl get pods -n cahoots"
echo "To stop port forwarding: pkill -f 'port-forward'" 