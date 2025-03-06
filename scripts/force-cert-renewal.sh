#!/bin/bash

echo "=== Current Certificate Status ==="
kubectl get certificate -n cahoots
echo ""

echo "=== Deleting existing certificate resources to force renewal ==="
# Delete any existing challenges
echo "Deleting challenges..."
kubectl delete challenge -n cahoots --all

# Delete any existing orders
echo "Deleting orders..."
kubectl delete order -n cahoots --all

# Delete any existing certificate requests
echo "Deleting certificate requests..."
kubectl delete certificaterequest -n cahoots --all

# Annotate the certificate to force renewal
echo "Annotating certificate to force renewal..."
kubectl annotate certificate cahoots-tls -n cahoots cert-manager.io/issue-temporary-certificate="true" --overwrite

# Delete the secret to force recreation
echo "Deleting TLS secret to force recreation..."
kubectl delete secret cahoots-tls -n cahoots

echo "=== Restarting cert-manager pods ==="
# Restart cert-manager pods to ensure clean state
kubectl rollout restart deployment -n cert-manager cert-manager
kubectl rollout restart deployment -n cert-manager cert-manager-webhook
kubectl rollout restart deployment -n cert-manager cert-manager-cainjector

echo "=== Waiting for cert-manager to restart ==="
kubectl rollout status deployment -n cert-manager cert-manager
kubectl rollout status deployment -n cert-manager cert-manager-webhook
kubectl rollout status deployment -n cert-manager cert-manager-cainjector

echo "=== Applying Network Policies ==="
# Apply the network policies first to ensure connectivity
echo "Applying cert-manager NetworkPolicy..."
kubectl apply -f k8s/cert-manager-network-policy.yaml

echo "Applying ACME solver NetworkPolicy..."
kubectl apply -f k8s/acme-solver-network-policy.yaml

echo "=== Reapplying SSL configuration ==="
# Reapply the cert-manager configuration
./scripts/apply-ssl-changes.sh

echo "=== Certificate renewal process initiated ==="
echo "Run './scripts/troubleshoot-cert.sh' to check the status and logs"
echo "If you still have connectivity issues, run './scripts/check-cluster-connectivity.sh'"