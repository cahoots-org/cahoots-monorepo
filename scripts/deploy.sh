#!/bin/bash

# Exit on error
set -e

# Default values
ENVIRONMENT="development"
REGION="us-west-2"
SKIP_TESTS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment|-e)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Deploying to $ENVIRONMENT environment in $REGION region"

# Run tests unless skipped
if [ "$SKIP_TESTS" = false ]; then
  echo "Running tests..."
  python -m pytest tests/
fi

# Build Docker images
echo "Building Docker images..."
services=("master" "project_manager" "developer" "ux_designer" "tester" "context_manager")
for service in "${services[@]}"; do
  echo "Building $service service..."
  docker build -t "ai-dev-team-$service:latest" -f "docker/$service/Dockerfile" .
done

# Initialize Terraform
echo "Initializing Terraform..."
cd terraform
terraform init -backend-config="environment/$ENVIRONMENT.tfbackend"

# Apply Terraform configuration
echo "Applying Terraform configuration..."
terraform workspace select "$ENVIRONMENT" || terraform workspace new "$ENVIRONMENT"
terraform plan -var-file="environment/$ENVIRONMENT.tfvars" -out=tfplan
terraform apply tfplan

# Update ECS services
echo "Updating ECS services..."
CLUSTER_NAME="ai-dev-team-${ENVIRONMENT}"
for service in "${services[@]}"; do
  aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "ai-dev-team-$service" \
    --force-new-deployment \
    --region "$REGION"
done

echo "Deployment complete!" 