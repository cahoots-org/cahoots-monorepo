from kubernetes import client, config
from typing import Optional

class K8sClient:
    def __init__(self):
        try:
            config.load_incluster_config()  # Load in-cluster config when running in k8s
        except config.ConfigException:
            config.load_kube_config()       # Fall back to local config
        self.apps_v1 = client.AppsV1Api()

    async def scale_deployment(
        self,
        deployment_name: str,
        replicas: int,
        namespace: str = "ai-dev-team"
    ) -> bool:
        """Scale a deployment to specified number of replicas."""
        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body={"spec": {"replicas": replicas}}
            )
            return True
        except Exception as e:
            print(f"Failed to scale deployment {deployment_name}: {e}")
            return False

_k8s_client: Optional[K8sClient] = None

def get_k8s_client() -> K8sClient:
    global _k8s_client
    if _k8s_client is None:
        _k8s_client = K8sClient()
    return _k8s_client 