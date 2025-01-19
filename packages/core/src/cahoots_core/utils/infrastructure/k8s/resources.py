"""Kubernetes resource management utilities."""
from typing import Dict, Optional
from ....utils.infrastructure import KubernetesClient, get_k8s_client

class ProjectResources:
    """Manages Kubernetes resources for a project."""

    def __init__(self, project_id: str, k8s_client: Optional[KubernetesClient] = None):
        """Initialize project resources.
        
        Args:
            project_id: The project ID
            k8s_client: Optional Kubernetes client, will create if not provided
        """
        self.project_id = project_id
        self.namespace = f"project-{project_id}"
        self.k8s_client = k8s_client or get_k8s_client()

    async def setup_namespace(self):
        """Create and configure project namespace."""
        # Create namespace if it doesn't exist
        await self.k8s_client.create_namespace(
            name=self.namespace,
            labels={
                "project": self.project_id,
                "managed-by": "cahoots"
            }
        )

    async def apply_resource_quotas(self, quotas: Dict[str, str]):
        """Apply resource quotas to project namespace.
        
        Args:
            quotas: Dictionary of resource quotas (cpu, memory, pods, etc)
        """
        await self.k8s_client.create_resource_quota(
            namespace=self.namespace,
            name=f"{self.namespace}-quota",
            spec={
                "hard": quotas
            }
        )

    async def apply_limit_range(self, limits: Dict[str, Dict[str, str]]):
        """Apply limit ranges to project namespace.
        
        Args:
            limits: Dictionary of container limits
        """
        await self.k8s_client.create_limit_range(
            namespace=self.namespace,
            name=f"{self.namespace}-limits",
            spec={
                "limits": [{
                    "type": "Container",
                    "default": limits.get("default", {}),
                    "defaultRequest": limits.get("defaultRequest", {}),
                    "max": limits.get("max", {}),
                    "min": limits.get("min", {})
                }]
            }
        )

    async def setup_network_policies(self):
        """Apply network policies for namespace isolation."""
        await self.k8s_client.create_network_policy(
            namespace=self.namespace,
            name=f"{self.namespace}-isolation",
            spec={
                "podSelector": {},
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [{
                    "from": [{
                        "namespaceSelector": {
                            "matchLabels": {
                                "project": self.project_id
                            }
                        }
                    }]
                }],
                "egress": [{
                    "to": [{
                        "namespaceSelector": {
                            "matchLabels": {
                                "project": self.project_id
                            }
                        }
                    }]
                }]
            }
        )

    async def setup_service_account(self):
        """Create service account for project workloads."""
        await self.k8s_client.create_service_account(
            namespace=self.namespace,
            name=f"{self.namespace}-sa",
            labels={
                "project": self.project_id
            }
        )

    async def initialize(self, resource_limits: Dict[str, str]):
        """Initialize all project resources.
        
        Args:
            resource_limits: Project resource limits
        """
        await self.setup_namespace()
        await self.apply_resource_quotas(resource_limits)
        await self.apply_limit_range({
            "default": {
                "cpu": "100m",
                "memory": "256Mi"
            },
            "defaultRequest": {
                "cpu": "50m",
                "memory": "128Mi"
            },
            "max": {
                "cpu": "2",
                "memory": "4Gi"
            }
        })
        await self.setup_network_policies()
        await self.setup_service_account()

    async def cleanup(self):
        """Cleanup all project resources."""
        await self.k8s_client.delete_namespace(self.namespace) 

def create_common_labels(name: str, component: str) -> dict:
    """Create common Kubernetes labels.
    
    Args:
        name: Resource name
        component: Component name
        
    Returns:
        dict: Common labels
    """
    return {
        "app.kubernetes.io/name": name,
        "app.kubernetes.io/component": component,
        "app.kubernetes.io/managed-by": "cahoots"
    } 