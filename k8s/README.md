# Kubernetes Configuration

This directory contains the Kubernetes configuration for the AI Dev Team project. The setup uses Kustomize for environment-specific configuration management.

## Directory Structure

```
k8s/
├── base/                   # Base configuration
│   ├── config.yaml        # ConfigMap with default settings
│   ├── secrets.yaml       # Secret templates
│   ├── workload.yaml      # Deployment and Service
│   ├── ingress.yaml       # Ingress configuration
│   └── kustomization.yaml # Base kustomization
└── overlays/              # Environment-specific overlays
    ├── production/
    │   └── kustomization.yaml  # Production settings
    └── development/
        └── kustomization.yaml  # Development settings
```

## Configuration Management

The configuration is split into:
- Base configuration (common across all environments)
- Environment-specific overlays (development, production)
- Secrets management

### Base Configuration

The base configuration defines:
- Core deployment settings
- Service configuration
- Ingress rules
- Default resource limits
- Common labels and annotations

### Environment Overlays

Environment-specific settings are managed through Kustomize overlays:

**Development:**
- Single replica
- Lower resource limits
- Debug mode enabled
- Development namespace

**Production:**
- Multiple replicas
- Higher resource limits
- Production-grade settings
- Production namespace

## Deployment

### Prerequisites

1. Kubernetes cluster access
2. `kubectl` installed and configured
3. Required secrets:
   - `REDIS_PASSWORD`
   - `JWT_SECRET_KEY`
   - `GITHUB_API_KEY`
   - `TRELLO_API_KEY`
   - `TRELLO_API_SECRET`
   - TLS certificates

### Setting up Secrets

1. Create a secrets file from the template:
   ```bash
   cp k8s/base/secrets.yaml k8s/base/secrets.local.yaml
   ```

2. Replace the placeholders with actual values:
   ```yaml
   redis:
     password: "your-redis-password"
   auth:
     secret_key: "your-jwt-secret"
   external:
     github_api_key: "your-github-key"
     trello_api_key: "your-trello-key"
     trello_api_secret: "your-trello-secret"
   ```

3. Create TLS secrets:
   ```bash
   kubectl create secret tls ai-dev-team-tls \
     --cert=path/to/tls.crt \
     --key=path/to/tls.key \
     -n ai-dev-team-prod
   ```

### Deployment Commands

**Development:**
```bash
# Create namespace
kubectl create namespace ai-dev-team-dev

# Apply configuration
kubectl apply -k k8s/overlays/development
```

**Production:**
```bash
# Create namespace
kubectl create namespace ai-dev-team-prod

# Apply configuration
kubectl apply -k k8s/overlays/production
```

### Verification

Check deployment status:
```bash
# List all resources
kubectl get all -n ai-dev-team-dev  # or ai-dev-team-prod

# Check pod logs
kubectl logs -f deployment/ai-dev-team -n ai-dev-team-dev

# Check pod health
kubectl describe pod -l app=ai-dev-team -n ai-dev-team-dev
```

## Monitoring

The deployment includes:
- Prometheus metrics endpoint at `/metrics`
- Health checks at `/health`
- Resource monitoring through Kubernetes

## Resource Management

### Development Resources
- CPU Request: 250m
- Memory Request: 256Mi
- CPU Limit: 1000m
- Memory Limit: 1Gi

### Production Resources
- CPU Request: 1000m
- Memory Request: 1Gi
- CPU Limit: 4000m
- Memory Limit: 4Gi

## Security

The configuration includes:
- TLS encryption
- Secret management
- Resource isolation
- Network policies
- ReadOnly filesystem mounts

## Troubleshooting

Common issues and solutions:

1. **Pod won't start:**
   ```bash
   kubectl describe pod <pod-name> -n ai-dev-team-dev
   ```

2. **Configuration issues:**
   ```bash
   kubectl get configmap ai-dev-team-config -n ai-dev-team-dev -o yaml
   ```

3. **Network issues:**
   ```bash
   kubectl get ingress -n ai-dev-team-dev
   kubectl describe ingress ai-dev-team -n ai-dev-team-dev
   ```

4. **Resource constraints:**
   ```bash
   kubectl top pod -n ai-dev-team-dev
   ```

## Maintenance

### Updating Configuration

1. Modify the appropriate files in `base/` or `overlays/`
2. Test changes in development:
   ```bash
   kubectl diff -k k8s/overlays/development
   ```
3. Apply changes:
   ```bash
   kubectl apply -k k8s/overlays/development
   ```

### Rolling Updates

The deployment is configured for zero-downtime updates:
```bash
kubectl set image deployment/ai-dev-team \
  ai-dev-team=ai-dev-team:new-tag -n ai-dev-team-prod
```

### Rollbacks

If needed, rollback to a previous version:
```bash
kubectl rollout undo deployment/ai-dev-team -n ai-dev-team-prod
``` 