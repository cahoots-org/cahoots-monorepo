"""Kubernetes client utilities."""
from typing import Optional
from kubernetes import client, config

class KubernetesClient:
    """Client for interacting with Kubernetes."""
    
    def __init__(self, namespace: Optional[str] = None):
        """Initialize the Kubernetes client.
        
        Args:
            namespace: The Kubernetes namespace to operate in
        """
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
            
        self.apps_v1 = client.AppsV1Api()
        self.namespace = namespace or "default"
        
    async def scale_deployment(self, deployment_name: str, replicas: int):
        """Scale a deployment to the specified number of replicas.
        
        Args:
            deployment_name: Name of the deployment to scale
            replicas: Desired number of replicas
        """
        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=self.namespace,
                body={"spec": {"replicas": replicas}}
            )
        except client.ApiException as e:
            if e.status == 404:
                raise ValueError(f"Deployment {deployment_name} not found")
            raise 