# SSL Certificate Troubleshooting Guide

## Problem

The Let's Encrypt certificate request is failing with a 502 error. This is happening because the Kubernetes NetworkPolicy configuration is too restrictive and doesn't allow the necessary traffic for the Let's Encrypt HTTP-01 challenge to work.

## Root Cause Analysis

After extensive troubleshooting, we identified two critical issues:

1. **Network Unreachable Error**: The ACME challenge solver pods cannot communicate with each other within the cluster due to overly restrictive NetworkPolicies.

2. **Missing Service Endpoints**: The logs show "Skipping service: no endpoints found" errors, indicating that some services don't have running pods to serve traffic.

## Solution

We've created several NetworkPolicies and scripts to address these issues:

### 1. Network Policy Fixes

#### Basic Cert-Manager Policy
The `k8s/cert-manager-network-policy.yaml` file contains NetworkPolicies that allow:
- Traffic to/from cert-manager
- Ingress traffic to your web services for the ACME challenge
- Traffic to/from your Traefik ingress controller

#### ACME Solver Policy
The `k8s/acme-solver-network-policy.yaml` file contains more specific NetworkPolicies:
- Targets pods with the `acme.cert-manager.io/http01-solver: "true"` label
- Allows all ingress/egress for ACME solver pods
- Enables communication between all pods in the cahoots namespace
- Permits external HTTP/HTTPS traffic for validation

### 2. Scripts

#### Apply SSL Changes
```bash
./scripts/apply-ssl-changes.sh
```
This script applies all NetworkPolicies, the ClusterIssuer, and Ingress configurations.

#### Force Certificate Renewal
```bash
./scripts/force-cert-renewal.sh
```
If the certificate is still not being issued after applying the NetworkPolicies, this script will:
- Delete existing certificate resources (challenges, orders, certificate requests)
- Annotate the certificate to force renewal
- Delete the TLS secret to force recreation
- Restart cert-manager pods
- Apply all NetworkPolicies
- Reapply the SSL configuration

#### Check ACME Challenge
```bash
./scripts/check-acme-challenge.sh
```
This script tests if the HTTP-01 challenge path is accessible by:
- Creating a test pod with a file at the `.well-known/acme-challenge` path
- Setting up a service and ingress for this pod
- Testing if the challenge file is accessible from the internet

#### Check Cluster Connectivity
```bash
./scripts/check-cluster-connectivity.sh
```
This script performs comprehensive connectivity checks:
- Verifies service endpoints exist
- Checks pod status
- Confirms external IP configuration
- Validates DNS resolution
- Tests internal connectivity to the ACME challenge path
- Verifies NetworkPolicy application

#### Troubleshoot Certificate
```bash
./scripts/troubleshoot-cert.sh
```
This script provides comprehensive diagnostics by:
- Checking certificate status
- Viewing cert-manager logs
- Checking network policies
- Testing DNS resolution
- Verifying HTTP challenge path accessibility

## Common Issues

1. **Restrictive NetworkPolicies**: The default NetworkPolicy blocks all ingress and egress traffic except for DNS, which prevents Let's Encrypt from validating your domain.

2. **DNS Configuration**: Ensure that the domain (cahoots.cc) is correctly pointing to your cluster's external IP.

3. **Missing Service Endpoints**: Ensure that your services have running pods. The "no endpoints found" error indicates that services don't have pods to serve traffic.

4. **Network Unreachable**: If you see "Network unreachable" errors, it indicates that pods cannot communicate with each other due to NetworkPolicy restrictions.

5. **Ingress Controller Configuration**: Make sure your Traefik ingress controller is properly configured to handle the `.well-known/acme-challenge` path.

6. **Certificate Resources**: Sometimes certificate resources can get stuck in a failed state. The force-cert-renewal.sh script helps clear these resources.

## Debugging Steps

1. First, check cluster connectivity to identify any issues:
   ```
   ./scripts/check-cluster-connectivity.sh
   ```

2. Apply the NetworkPolicy fixes:
   ```
   ./scripts/apply-ssl-changes.sh
   ```

3. If the certificate is still not ready, check if the ACME challenge path is accessible:
   ```
   ./scripts/check-acme-challenge.sh
   ```

4. If the ACME challenge test fails, run the troubleshooting script to get more information:
   ```
   ./scripts/troubleshoot-cert.sh
   ```

5. If all else fails, force a complete renewal of the certificate:
   ```
   ./scripts/force-cert-renewal.sh
   ```

## Additional Resources

- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Kubernetes NetworkPolicy Documentation](https://kubernetes.io/docs/concepts/services-networking/network-policies/)