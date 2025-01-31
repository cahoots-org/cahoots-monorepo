"""Kubernetes agent management utilities."""
from typing import Dict, List, Optional
from ....utils.infrastructure import KubernetesClient, get_k8s_client

class AgentDeployment:
    """Manages agent deployments for a project."""

    def __init__(self, project_id: str, k8s_client: Optional[KubernetesClient] = None):
        """Initialize agent deployment manager.
        
        Args:
            project_id: The project ID
            k8s_client: Optional Kubernetes client, will create if not provided
        """
        self.project_id = project_id
        self.namespace = f"project-{project_id}"
        self.k8s_client = k8s_client or get_k8s_client()

    def _get_agent_env(self, agent_type: str, config: Dict) -> List[Dict]:
        """Get environment variables for agent deployment.
        
        Args:
            agent_type: Type of agent (developer, qa, etc)
            config: Agent configuration
            
        Returns:
            List of environment variable definitions
        """
        return [
            {
                "name": "PROJECT_ID",
                "value": self.project_id
            },
            {
                "name": "AGENT_TYPE",
                "value": agent_type
            },
            {
                "name": "REDIS_NAMESPACE",
                "value": f"project:{self.project_id}"
            },
            {
                "name": "DB_SCHEMA",
                "value": f"project_{self.project_id}"
            },
            {
                "name": "CONFIG",
                "value": str(config)
            }
        ]

    def _get_agent_resources(self, tier: str) -> Dict:
        """Get resource requirements based on tier.
        
        Args:
            tier: Service tier (basic, premium, enterprise)
            
        Returns:
            Resource requirements dictionary
        """
        resources = {
            "basic": {
                "requests": {
                    "cpu": "100m",
                    "memory": "256Mi"
                },
                "limits": {
                    "cpu": "200m",
                    "memory": "512Mi"
                }
            },
            "premium": {
                "requests": {
                    "cpu": "200m",
                    "memory": "512Mi"
                },
                "limits": {
                    "cpu": "500m",
                    "memory": "1Gi"
                }
            },
            "enterprise": {
                "requests": {
                    "cpu": "500m",
                    "memory": "1Gi"
                },
                "limits": {
                    "cpu": "1",
                    "memory": "2Gi"
                }
            }
        }
        return resources.get(tier, resources["basic"])

    async def deploy_agent(self, agent_type: str, config: Dict, tier: str = "basic"):
        """Deploy an agent for the project.
        
        Args:
            agent_type: Type of agent to deploy
            config: Agent configuration
            tier: Service tier for resource allocation
        """
        deployment_name = f"{agent_type}-{self.project_id}"
        
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": deployment_name,
                "namespace": self.namespace,
                "labels": {
                    "app": deployment_name,
                    "project": self.project_id,
                    "agent-type": agent_type
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": deployment_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": deployment_name,
                            "project": self.project_id,
                            "agent-type": agent_type
                        }
                    },
                    "spec": {
                        "serviceAccountName": f"{self.namespace}-sa",
                        "containers": [{
                            "name": agent_type,
                            "image": f"cahoots/agent-{agent_type}:latest",
                            "env": self._get_agent_env(agent_type, config),
                            "resources": self._get_agent_resources(tier),
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": 8000
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/ready",
                                    "port": 8000
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5
                            }
                        }]
                    }
                }
            }
        }
        
        await self.k8s_client.create_deployment(deployment)

    async def scale_agent(self, agent_type: str, replicas: int):
        """Scale an agent deployment.
        
        Args:
            agent_type: Type of agent to scale
            replicas: Number of replicas
        """
        deployment_name = f"{agent_type}-{self.project_id}"
        await self.k8s_client.scale_deployment(
            name=deployment_name,
            namespace=self.namespace,
            replicas=replicas
        )

    async def delete_agent(self, agent_type: str):
        """Delete an agent deployment.
        
        Args:
            agent_type: Type of agent to delete
        """
        deployment_name = f"{agent_type}-{self.project_id}"
        await self.k8s_client.delete_deployment(
            name=deployment_name,
            namespace=self.namespace
        )

    async def get_agent_status(self, agent_type: str) -> Dict:
        """Get status of an agent deployment.
        
        Args:
            agent_type: Type of agent to check
            
        Returns:
            Deployment status dictionary
        """
        deployment_name = f"{agent_type}-{self.project_id}"
        return await self.k8s_client.get_deployment_status(
            name=deployment_name,
            namespace=self.namespace
        ) 