#!/bin/bash

# This script creates a test file in the .well-known/acme-challenge path
# and checks if it's accessible from the internet

# Get the external IP of the ingress controller
INGRESS_IP=$(kubectl get svc -n kube-system -l app.kubernetes.io/name=traefik -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')

if [ -z "$INGRESS_IP" ]; then
  echo "Could not determine ingress controller IP. Using domain name instead."
  HOST="cahoots.cc"
else
  echo "Ingress controller external IP: $INGRESS_IP"
  HOST="$INGRESS_IP"
fi

# Create a test pod to serve the acme-challenge test file
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: acme-test
  namespace: cahoots
  labels:
    app: acme-test
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    ports:
    - containerPort: 80
    volumeMounts:
    - name: workdir
      mountPath: /usr/share/nginx/html
  initContainers:
  - name: install
    image: busybox
    command:
    - sh
    - -c
    - |
      mkdir -p /work-dir/.well-known/acme-challenge
      echo "acme-test-file-content" > /work-dir/.well-known/acme-challenge/test-file
    volumeMounts:
    - name: workdir
      mountPath: "/work-dir"
  volumes:
  - name: workdir
    emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: acme-test
  namespace: cahoots
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: acme-test
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: acme-test
  namespace: cahoots
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  rules:
  - host: cahoots.cc
    http:
      paths:
      - path: /.well-known/acme-challenge/
        pathType: Prefix
        backend:
          service:
            name: acme-test
            port:
              number: 80
EOF

echo "Waiting for test pod to be ready..."
kubectl wait --for=condition=ready pod -n cahoots acme-test --timeout=60s

echo "Testing HTTP-01 challenge path accessibility..."
echo "Trying to access: http://cahoots.cc/.well-known/acme-challenge/test-file"
echo "Expected content: acme-test-file-content"
echo ""
echo "Testing with curl:"
curl -v http://cahoots.cc/.well-known/acme-challenge/test-file

if [ $? -ne 0 ]; then
  echo ""
  echo "Trying with IP address instead of domain name..."
  if [ -n "$INGRESS_IP" ]; then
    curl -v -H "Host: cahoots.cc" http://$INGRESS_IP/.well-known/acme-challenge/test-file
  fi
fi

echo ""
echo "Cleaning up test resources..."
kubectl delete ingress -n cahoots acme-test
kubectl delete service -n cahoots acme-test
kubectl delete pod -n cahoots acme-test

echo ""
echo "If the curl command failed or returned an error, the Let's Encrypt validation will also fail."
echo "Check your network policies, DNS configuration, and ingress controller setup."