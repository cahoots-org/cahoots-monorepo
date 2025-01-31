#!/bin/bash
set -e

# Default environment
ENV=${ENV:-dev}
NAMESPACE=${NAMESPACE:-cahoots}
PROJECT=${PROJECT:-cahoots}

# Load environment-specific variables
if [ -f ".env.${ENV}" ]; then
    echo "Loading ${ENV} environment variables..."
    source ".env.${ENV}"
fi

# Ensure namespace exists
ensure_namespace() {
    if ! kubectl get namespace ${NAMESPACE} >/dev/null 2>&1; then
        echo "Creating namespace ${NAMESPACE}..."
        kubectl create namespace ${NAMESPACE}
    fi
}

# Apply Kubernetes configurations
apply_configs() {
    echo "Applying Kubernetes configurations for ${ENV} environment..."
    
    # Apply configurations in order
    for config in configmap secret service deployment ingress; do
        if ls k8s/${ENV}/${config}*.yaml >/dev/null 2>&1; then
            echo "Applying ${config} configurations..."
            kubectl apply -f k8s/${ENV}/${config}*.yaml -n ${NAMESPACE}
        fi
    done
}

# Wait for deployments
wait_for_deployments() {
    echo "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available deployment --all -n ${NAMESPACE} --timeout=300s
}

# Check deployment status
check_status() {
    echo "Checking deployment status..."
    kubectl get pods -n ${NAMESPACE}
    kubectl get services -n ${NAMESPACE}
}

# Main deployment process
main() {
    ensure_namespace
    apply_configs
    wait_for_deployments
    check_status
    
    echo "Deployment complete for ${ENV} environment!"
}

# Run main function
main 