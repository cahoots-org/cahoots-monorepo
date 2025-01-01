# Environment Overlays

This directory contains environment-specific Kubernetes configurations that build upon the base configuration.

## Structure

```
overlays/
├── development/
│   └── kustomization.yaml
└── production/
    └── kustomization.yaml
```

## Development Environment

The development overlay (`development/`) is optimized for local development and testing:

### Features
- Single replica deployment
- Lower resource limits
- Debug mode enabled
- Development namespace isolation

### Configuration
```yaml
namespace: ai-dev-team-dev
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Environment Variables
```yaml
ENV: development
LOG_LEVEL: DEBUG
DEBUG: "true"
```

## Production Environment

The production overlay (`production/`) is optimized for reliability and performance:

### Features
- Multi-replica deployment
- Higher resource limits
- Production-grade settings
- Production namespace isolation

### Configuration
```yaml
namespace: ai-dev-team-prod
resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 4Gi
```

### Environment Variables
```yaml
ENV: production
LOG_LEVEL: INFO
DEBUG: "false"
```

## Usage

### Development Deployment
```bash
# Preview changes
kubectl kustomize overlays/development

# Apply changes
kubectl apply -k overlays/development
```

### Production Deployment
```bash
# Preview changes
kubectl kustomize overlays/production

# Apply changes
kubectl apply -k overlays/production
```

## Customization

### Adding New Environment Variables
1. Add to the configMapGenerator in the appropriate kustomization.yaml:
   ```yaml
   configMapGenerator:
     - name: ai-dev-team-config
       behavior: merge
       literals:
         - NEW_VAR=value
   ```

### Modifying Resource Limits
1. Update the patches section in kustomization.yaml:
   ```yaml
   patches:
     - target:
         kind: Deployment
         name: ai-dev-team
       patch: |
         - op: replace
           path: /spec/template/spec/containers/0/resources/requests/cpu
           value: new-value
   ```

### Adding New Resources
1. Create the resource YAML in the overlay directory
2. Add it to the resources list in kustomization.yaml:
   ```yaml
   resources:
     - ../../base
     - new-resource.yaml
   ```

## Best Practices

1. Always test changes in development first
2. Use `kubectl diff -k` to preview changes
3. Keep environment-specific settings in overlays
4. Document significant changes
5. Use version control for all changes

## Troubleshooting

### Common Issues

1. **Wrong Environment**
   - Check current namespace
   - Verify environment variables
   ```bash
   kubectl get configmap ai-dev-team-config -o yaml
   ```

2. **Resource Constraints**
   - Monitor resource usage
   ```bash
   kubectl top pods -n ai-dev-team-dev
   ```

3. **Configuration Issues**
   - Validate kustomization
   ```bash
   kubectl kustomize . | kubectl apply --dry-run=client -f -
   ```

### Validation

Always validate changes before applying:
```bash
# Validate syntax
kubectl kustomize . | kubeval

# Check differences
kubectl diff -k .

# Dry run
kubectl apply -k . --dry-run=client
``` 