#!/bin/bash

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# Error handling
handle_error() {
  local exit_code=$1
  local line_no=$2
  echo "Error on line $line_no: Command exited with status $exit_code"
  cleanup
  exit 1
}

trap 'handle_error $? $LINENO' ERR

# Cleanup function
cleanup() {
  echo "Cleaning up..."
  # Add cleanup tasks if needed
}

# Check prerequisites
check_prerequisites() {
  local missing_deps=()

  echo "Checking prerequisites..."
  
  # Check required commands
  local required_cmds=("kubectl" "docker" "openssl")
  for cmd in "${required_cmds[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing_deps+=("$cmd")
    fi
  done

  # Check if Docker Desktop Kubernetes is running
  if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Kubernetes is not running. Please start Docker Desktop and enable Kubernetes."
    exit 1
  fi

  # Check for configuration files
  if [ ! -f "k8s/overlays/development/kustomization.yaml" ]; then
    echo "Error: Missing development kustomization file"
    exit 1
  fi

  # Check for secrets
  if [ ! -f "k8s/overlays/development/secrets.yaml" ]; then
    echo "Error: Missing development secrets file"
    echo "Please copy k8s/base/secrets.yaml.template to k8s/overlays/development/secrets.yaml and fill in the values"
    exit 1
  fi

  if [ ${#missing_deps[@]} -ne 0 ]; then
    echo "Missing required dependencies: ${missing_deps[*]}"
    exit 1
  fi
}

# Validate configuration
validate_config() {
  echo "Validating Kubernetes configurations..."
  if ! kubectl kustomize k8s/overlays/development > /dev/null; then
    echo "Error: Invalid Kubernetes configurations"
    exit 1
  fi
}

# Build images with proper versioning
build_images() {
  echo "Building images..."
  local version="dev-$(git rev-parse --short HEAD)"
  
  # Build each service image
  local services=("master" "pm" "developer" "ux" "tester")
  for service in "${services[@]}"; do
    echo "Building ai-dev-team-${service}:${version}..."
    docker build \
      --build-arg SERVICE_NAME="${service}" \
      --build-arg VERSION="${version}" \
      -t "ai-dev-team-${service}:${version}" \
      -f Dockerfile .
    
    # Tag as dev for local development
    docker tag "ai-dev-team-${service}:${version}" "ai-dev-team-${service}:dev"
  done
}

# Deploy to local cluster
deploy() {
  echo "Deploying to local Kubernetes cluster..."
  
  # Create namespace if it doesn't exist
  kubectl create namespace ai-dev-team-dev --dry-run=client -o yaml | kubectl apply -f -

  # Apply configurations
  kubectl apply -k k8s/overlays/development

  # Wait for Redis to be ready first
  echo "Waiting for Redis to be ready..."
  kubectl wait --namespace ai-dev-team-dev \
    --for=condition=ready pod \
    --selector=app=redis \
    --timeout=60s

  # Wait for service pods to be ready
  echo "Waiting for service pods to be ready..."
  kubectl wait --namespace ai-dev-team-dev \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/part-of=ai-dev-team \
    --timeout=300s
}

# Main execution
main() {
  check_prerequisites
  validate_config
  build_images
  deploy

  echo "Local Kubernetes deployment complete!"
  echo "You can access the services at:"
  echo "- Master service: http://localhost:8000"
  echo "- PM service: http://localhost:8001"
  echo "- Developer service: http://localhost:8002"
  echo "- UX service: http://localhost:8003"
  echo "- Tester service: http://localhost:8004"

  echo -e "\nPod status:"
  kubectl get pods -n ai-dev-team-dev

  echo -e "\nTo view logs:"
  echo "kubectl logs -n ai-dev-team-dev -l app.kubernetes.io/part-of=ai-dev-team -f"
}

main "$@" 