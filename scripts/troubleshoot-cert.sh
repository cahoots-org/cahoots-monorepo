#!/bin/bash

echo "=== Certificate Status ==="
kubectl get certificate -n cahoots
echo ""

echo "=== Certificate Request Status ==="
kubectl get certificaterequest -n cahoots
echo ""

echo "=== Order Status ==="
kubectl get order -n cahoots
echo ""

echo "=== Challenge Status ==="
kubectl get challenge -n cahoots
echo ""

echo "=== Cert Manager Logs ==="
kubectl logs -n cert-manager -l app.kubernetes.io/instance=cert-manager --tail=50
echo ""

echo "=== Cert Manager Controller Logs ==="
kubectl logs -n cert-manager -l app.kubernetes.io/name=cert-manager,app.kubernetes.io/component=controller --tail=50
echo ""

echo "=== Cert Manager Webhook Logs ==="
kubectl logs -n cert-manager -l app.kubernetes.io/name=cert-manager,app.kubernetes.io/component=webhook --tail=50
echo ""

echo "=== Ingress Controller Logs ==="
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik --tail=50
echo ""

echo "=== Network Policy Check ==="
echo "Checking if NetworkPolicies are properly configured..."
kubectl get networkpolicy -n cahoots
kubectl get networkpolicy -n cert-manager
echo ""

echo "=== DNS Resolution Check ==="
echo "Checking if cahoots.cc resolves properly..."
nslookup cahoots.cc
echo ""

echo "=== HTTP Challenge Path Check ==="
echo "Checking if the HTTP challenge path is accessible..."
echo "Try accessing: http://cahoots.cc/.well-known/acme-challenge/test-file"
echo "If you get a 404 Not Found, that's expected. If you get a connection error, there might be network issues."