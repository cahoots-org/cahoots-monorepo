#!/bin/bash

echo "=== Checking Service Endpoints ==="
echo "Master service endpoints:"
kubectl get endpoints master -n cahoots

echo "Web-client service endpoints:"
kubectl get endpoints web-client -n cahoots

echo "Traefik ingress controller endpoints:"
kubectl get endpoints -n kube-system -l app.kubernetes.io/name=traefik

echo ""
echo "=== Checking Pod Status ==="
echo "Master pods:"
kubectl get pods -n cahoots -l app=master

echo "Web-client pods:"
kubectl get pods -n cahoots -l app=web-client

echo "Traefik ingress controller pods:"
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik

echo ""
echo "=== Checking External IP ==="
echo "Ingress controller external IP:"
INGRESS_IP=$(kubectl get svc -n kube-system -l app.kubernetes.io/name=traefik -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')
echo "External IP: $INGRESS_IP"

echo ""
echo "=== Checking if External IP matches DNS ==="
echo "DNS resolution for cahoots.cc:"
nslookup cahoots.cc

if [ -n "$INGRESS_IP" ]; then
  echo ""
  echo "Comparing resolved IP with ingress controller IP:"
  echo "Ingress controller IP: $INGRESS_IP"
  echo "Resolved IP for cahoots.cc: $(dig +short cahoots.cc)"
  
  if [ "$(dig +short cahoots.cc)" = "$INGRESS_IP" ]; then
    echo "✅ DNS is correctly pointing to your ingress controller"
  else
    echo "❌ DNS is NOT pointing to your ingress controller"
    echo "You need to update your DNS records to point cahoots.cc to $INGRESS_IP"
  fi
fi

echo ""
echo "=== Testing HTTP-01 Challenge Path Locally ==="
echo "Trying to access the challenge path from inside the cluster:"

# Create a temporary pod to test connectivity
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -v http://cm-acme-http-solver-nmp9h.cahoots.svc/.well-known/acme-challenge/test-file

echo ""
echo "=== Checking NetworkPolicy Application ==="
echo "Verifying if the NetworkPolicies are being enforced:"
kubectl describe networkpolicy allow-acme-challenge -n cahoots
kubectl describe networkpolicy allow-ingress-controller -n cahoots
kubectl describe networkpolicy allow-cert-manager -n cert-manager

echo ""
echo "=== Recommendations ==="
echo "Based on the results above:"
echo "1. If services have no endpoints, you need to ensure your pods are running"
echo "2. If DNS doesn't match your ingress controller IP, update your DNS records"
echo "3. If NetworkPolicies are not properly applied, try reapplying them"
echo ""
echo "You can fix these issues and then run ./scripts/force-cert-renewal.sh to retry"