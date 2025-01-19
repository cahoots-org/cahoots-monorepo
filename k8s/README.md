# Kubernetes Deployment Guide

This directory contains the Kubernetes configuration for deploying the Cahoots microservices.

## Structure

```
k8s/
├── base/                   # Base Kubernetes configuration
│   ├── configmap.yaml     # Common environment variables
│   ├── deployments.yaml   # Service deployments
│   ├── kustomization.yaml # Base kustomization
│   ├── redis.yaml         # Redis deployment
│   ├── scripts/           # Utility scripts
│   ├── secret.yaml        # Secret configuration
│   └── services.yaml      # Service definitions
└── overlays/              # Environment-specific configurations
    └── development/       # Development environment
        ├── kustomization.yaml
        └── patches/       # Environment-specific patches
            └── configmap.yaml

```

## Prerequisites

1. Kubernetes cluster (local or remote)
2. kubectl installed and configured
3. Docker installed
4. Environment variables set:
   - `GITHUB_API_KEY`: GitHub API token
   - `TOGETHER_API_KEY`: Together AI API key

## Local Development

1. Create a `.env` file in the project root:
   ```
   GITHUB_API_KEY=your_github_token
   TOGETHER_API_KEY=your_together_token
   ```

2. Run the deployment script:
   ```bash
   ./scripts/run_local.sh
   ```

   This will:
   - Build Docker images for all services
   - Apply Kubernetes configurations
   - Deploy all services
   - Set up Redis
   - Configure health checks

3. Access the services:
   - Main API: http://localhost:80
   - Individual services: http://localhost:8000 (through port-forwarding)

## Monitoring

1. View service logs:
   ```bash
   kubectl logs -f deployment/cahoots-master -n cahoots
   ```

2. Check pod status:
   ```bash
   kubectl get pods -n cahoots
   ```

3. Access Kubernetes dashboard:
   ```bash
   kubectl proxy
   ```

## Configuration

1. Base Configuration (`base/`):
   - Common settings for all environments
   - Service definitions
   - Resource limits
   - Health checks

2. Development Configuration (`overlays/development/`):
   - Development-specific settings
   - Environment variables
   - Service overrides

## Troubleshooting

1. If pods are in `CrashLoopBackOff`:
   ```bash
   kubectl describe pod <pod-name> -n cahoots
   kubectl logs <pod-name> -n cahoots
   ```

2. Check ConfigMaps and Secrets:
   ```bash
   kubectl get configmap -n cahoots
   kubectl get secret -n cahoots
   ```

3. Verify environment variables:
   ```bash
   kubectl exec <pod-name> -n cahoots -- env
   ```

4. Reset deployment:
   ```bash
   kubectl delete deployment --all -n cahoots
   kubectl delete pod --all -n cahoots
   ./scripts/run_local.sh
   ``` 