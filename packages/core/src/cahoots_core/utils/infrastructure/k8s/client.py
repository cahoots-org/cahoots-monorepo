"""Kubernetes client for managing cluster resources."""
from typing import Optional, Dict, Any, List
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

logger = logging.getLogger(__name__)

class KubernetesClient:
    """Client for interacting with Kubernetes cluster resources."""
    
    def __init__(self, namespace: str = None):
        """Initialize the Kubernetes client.
        
        Args:
            namespace: The Kubernetes namespace to operate in (defaults to cahoots)
        """
        try:
            config.load_incluster_config()  # Load in-cluster config when running in k8s
        except config.ConfigException:
            config.load_kube_config()       # Fall back to local config
            
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.namespace = namespace or "cahoots"
        
    async def scale_deployment(
        self,
        deployment_name: str,
        replicas: int,
        namespace: Optional[str] = None
    ) -> bool:
        """Scale a deployment to the specified number of replicas.
        
        Args:
            deployment_name: Name of the deployment to scale
            replicas: Desired number of replicas
            namespace: Optional namespace override
            
        Returns:
            True if scaling succeeded, False otherwise
            
        Raises:
            ValueError: If deployment not found
        """
        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace or self.namespace,
                body={"spec": {"replicas": replicas}}
            )
            logger.info(
                f"Scaled deployment {deployment_name} to {replicas} replicas"
            )
            return True
            
        except ApiException as e:
            if e.status == 404:
                raise ValueError(f"Deployment {deployment_name} not found")
            logger.error(
                f"Failed to scale deployment {deployment_name}: {str(e)}"
            )
            return False
            
    async def get_deployment_status(
        self,
        deployment_name: str,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current status of a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Optional namespace override
            
        Returns:
            Dictionary with deployment status
            
        Raises:
            ValueError: If deployment not found
        """
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace or self.namespace
            )
            
            return {
                "name": deployment.metadata.name,
                "replicas": deployment.spec.replicas,
                "available": deployment.status.available_replicas or 0,
                "ready": deployment.status.ready_replicas or 0,
                "updated": deployment.status.updated_replicas or 0,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message
                    }
                    for c in (deployment.status.conditions or [])
                ]
            }
            
        except ApiException as e:
            if e.status == 404:
                raise ValueError(f"Deployment {deployment_name} not found")
            logger.error(
                f"Failed to get deployment status for {deployment_name}: {str(e)}"
            )
            raise
            
    async def list_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List pods in the namespace.
        
        Args:
            namespace: Optional namespace override
            label_selector: Optional label selector to filter pods
            
        Returns:
            List of pod information dictionaries
        """
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace or self.namespace,
                label_selector=label_selector
            )
            
            return [
                {
                    "name": pod.metadata.name,
                    "phase": pod.status.phase,
                    "ip": pod.status.pod_ip,
                    "node": pod.spec.node_name,
                    "containers": [
                        {
                            "name": c.name,
                            "ready": c.ready,
                            "restarts": c.restart_count,
                            "image": c.image
                        }
                        for c in pod.status.container_statuses or []
                    ] if pod.status.container_statuses else []
                }
                for pod in pods.items
            ]
            
        except ApiException as e:
            logger.error(f"Failed to list pods: {str(e)}")
            raise
            
    async def create_job(
        self,
        name: str,
        image: str,
        command: List[str],
        namespace: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None
    ) -> bool:
        """Create a Kubernetes job.
        
        Args:
            name: Name of the job
            image: Container image to use
            command: Command to run in container
            namespace: Optional namespace override
            env_vars: Optional environment variables
            cpu_limit: Optional CPU limit (e.g. "100m")
            memory_limit: Optional memory limit (e.g. "256Mi")
            
        Returns:
            True if job creation succeeded, False otherwise
        """
        try:
            # Prepare container environment
            env = []
            if env_vars:
                env = [
                    client.V1EnvVar(name=k, value=v)
                    for k, v in env_vars.items()
                ]
                
            # Prepare resource limits
            resources = None
            if cpu_limit or memory_limit:
                resources = client.V1ResourceRequirements(
                    limits={
                        "cpu": cpu_limit,
                        "memory": memory_limit
                    }
                )
                
            # Create job spec
            job = client.V1Job(
                metadata=client.V1ObjectMeta(name=name),
                spec=client.V1JobSpec(
                    template=client.V1PodTemplateSpec(
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name=name,
                                    image=image,
                                    command=command,
                                    env=env,
                                    resources=resources
                                )
                            ],
                            restart_policy="Never"
                        )
                    )
                )
            )
            
            # Create the job
            self.batch_v1.create_namespaced_job(
                namespace=namespace or self.namespace,
                body=job
            )
            
            logger.info(f"Created job {name}")
            return True
            
        except ApiException as e:
            logger.error(f"Failed to create job {name}: {str(e)}")
            return False
            
    async def delete_job(
        self,
        name: str,
        namespace: Optional[str] = None
    ) -> bool:
        """Delete a Kubernetes job.
        
        Args:
            name: Name of the job to delete
            namespace: Optional namespace override
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            self.batch_v1.delete_namespaced_job(
                name=name,
                namespace=namespace or self.namespace,
                body=client.V1DeleteOptions(
                    propagation_policy="Background"
                )
            )
            
            logger.info(f"Deleted job {name}")
            return True
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Job {name} not found")
                return True
            logger.error(f"Failed to delete job {name}: {str(e)}")
            return False

# Global client instance
_k8s_client: Optional[KubernetesClient] = None

def get_k8s_client(namespace: Optional[str] = None) -> KubernetesClient:
    """Get or create the global Kubernetes client instance.
    
    Args:
        namespace: Optional namespace override
        
    Returns:
        KubernetesClient instance
    """
    global _k8s_client
    if _k8s_client is None:
        _k8s_client = KubernetesClient(namespace)
    return _k8s_client 