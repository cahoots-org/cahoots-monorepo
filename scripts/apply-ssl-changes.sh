#!/bin/bash

# Apply the cert-manager NetworkPolicy to allow traffic for ACME challenges
echo "Applying cert-manager NetworkPolicy..."
kubectl apply -f k8s/cert-manager-network-policy.yaml

# Apply the ACME solver NetworkPolicy to allow traffic to/from solver pods
echo "Applying ACME solver NetworkPolicy..."
kubectl apply -f k8s/acme-solver-network-policy.yaml

# Apply the cert-manager ClusterIssuer
echo "Applying cert-manager ClusterIssuer..."
kubectl apply -f k8s/cert-manager.yaml

# Apply the updated ingress with TLS configuration
echo "Applying ingress with TLS configuration..."
kubectl apply -f k8s/ingress.yaml

# Check the status of the certificate
echo "Waiting for certificate to be issued..."
sleep 10
kubectl get certificate -n cahoots

echo "SSL configuration applied. It may take a few minutes for the certificate to be issued."
echo "You can check the status with: kubectl get certificate -n cahoots"
echo "You can check cert-manager logs with: kubectl logs -n cert-manager -l app.kubernetes.io/instance=cert-manager"
echo "If you still have issues, run: ./scripts/check-cluster-connectivity.sh"