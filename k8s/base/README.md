# Base Configuration

This directory contains the base Kubernetes configuration that is common across all environments.

## Files

### `config.yaml`
Contains the ConfigMap with default application settings:
- Environment variables
- Redis configuration
- Authentication settings
- Service URLs and timeouts

### `secrets.yaml`
Template for sensitive information:
- Redis password
- JWT secret key
- External service API keys
- TLS certificates

### `workload.yaml`
Core deployment configuration:
- Pod specification
- Resource requests/limits
- Health checks
- Volume mounts
- Service definition

### `ingress.yaml`
Ingress configuration:
- TLS settings
- Path routing
- Load balancer annotations

### `kustomization.yaml`
Kustomize configuration:
- Resource inclusion
- Common labels
- ConfigMap and Secret generation
- Image tag management

## Usage

The base configuration is not meant to be deployed directly. Instead, use one of the environment overlays in `../overlays/`.

## Configuration Details

### Resource Defaults
```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### Health Checks
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 5
  periodSeconds: 10

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 15
  periodSeconds: 20
```

### Volume Mounts
```yaml
volumeMounts:
- name: config
  mountPath: /config
  readOnly: true
- name: secrets
  mountPath: /config/secrets.yaml
  subPath: secrets.yaml
  readOnly: true
- name: tls
  mountPath: /certs
  readOnly: true
```

## Customization

To modify the base configuration:

1. Edit the relevant YAML file
2. Update the kustomization.yaml if adding/removing resources
3. Test changes through an overlay:
   ```bash
   kubectl kustomize ../overlays/development
   ```

## Notes

- All sensitive values use placeholders (`${VARIABLE}`)
- TLS certificates should be managed separately
- Resource limits can be overridden in overlays
- Service names use internal Kubernetes DNS 