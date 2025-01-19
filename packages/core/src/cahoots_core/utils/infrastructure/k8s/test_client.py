"""Unit tests for Kubernetes client module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from kubernetes.client.rest import ApiException
from kubernetes import client

from .client import KubernetesClient, get_k8s_client

@pytest.fixture
def mock_k8s_apis():
    """Mock Kubernetes API clients."""
    with patch("kubernetes.client.CoreV1Api") as mock_core_v1, \
         patch("kubernetes.client.AppsV1Api") as mock_apps_v1, \
         patch("kubernetes.client.BatchV1Api") as mock_batch_v1, \
         patch("kubernetes.config.load_incluster_config"), \
         patch("kubernetes.config.load_kube_config"):
             
        mock_core_v1_instance = Mock()
        mock_apps_v1_instance = Mock()
        mock_batch_v1_instance = Mock()
        
        mock_core_v1.return_value = mock_core_v1_instance
        mock_apps_v1.return_value = mock_apps_v1_instance
        mock_batch_v1.return_value = mock_batch_v1_instance
        
        yield {
            "core_v1": mock_core_v1_instance,
            "apps_v1": mock_apps_v1_instance,
            "batch_v1": mock_batch_v1_instance
        }

@pytest.fixture
def k8s_client(mock_k8s_apis):
    """Create a KubernetesClient instance with mocked APIs."""
    return KubernetesClient()

@pytest.mark.asyncio
async def test_scale_deployment_success(k8s_client, mock_k8s_apis):
    """Test successful deployment scaling."""
    deployment_name = "test-deployment"
    replicas = 3
    
    result = await k8s_client.scale_deployment(deployment_name, replicas)
    
    assert result is True
    mock_k8s_apis["apps_v1"].patch_namespaced_deployment_scale.assert_called_once_with(
        name=deployment_name,
        namespace="cahoots",
        body={"spec": {"replicas": replicas}}
    )

@pytest.mark.asyncio
async def test_scale_deployment_not_found(k8s_client, mock_k8s_apis):
    """Test deployment scaling when deployment not found."""
    mock_k8s_apis["apps_v1"].patch_namespaced_deployment_scale.side_effect = \
        ApiException(status=404)
        
    with pytest.raises(ValueError, match="Deployment test-deployment not found"):
        await k8s_client.scale_deployment("test-deployment", 3)

@pytest.mark.asyncio
async def test_get_deployment_status_success(k8s_client, mock_k8s_apis):
    """Test successful deployment status retrieval."""
    deployment = Mock()
    deployment.metadata.name = "test-deployment"
    deployment.spec.replicas = 3
    deployment.status.available_replicas = 2
    deployment.status.ready_replicas = 2
    deployment.status.updated_replicas = 2
    deployment.status.conditions = [
        Mock(
            type="Available",
            status="True",
            reason="MinimumReplicasAvailable",
            message="Deployment has minimum availability."
        )
    ]
    
    mock_k8s_apis["apps_v1"].read_namespaced_deployment.return_value = deployment
    
    status = await k8s_client.get_deployment_status("test-deployment")
    
    assert status["name"] == "test-deployment"
    assert status["replicas"] == 3
    assert status["available"] == 2
    assert status["ready"] == 2
    assert status["updated"] == 2
    assert len(status["conditions"]) == 1
    assert status["conditions"][0]["type"] == "Available"

@pytest.mark.asyncio
async def test_list_pods_success(k8s_client, mock_k8s_apis):
    """Test successful pod listing."""
    pod = Mock()
    pod.metadata.name = "test-pod"
    pod.status.phase = "Running"
    pod.status.pod_ip = "10.0.0.1"
    pod.spec.node_name = "node-1"
    container_status = Mock(
        name="container-1",
        ready=True,
        restart_count=0,
        image="test:latest"
    )
    pod.status.container_statuses = [container_status]
    
    mock_response = Mock()
    mock_response.items = [pod]
    mock_k8s_apis["core_v1"].list_namespaced_pod.return_value = mock_response
    
    pods = await k8s_client.list_pods()
    
    assert len(pods) == 1
    assert pods[0]["name"] == "test-pod"
    assert pods[0]["phase"] == "Running"
    assert pods[0]["ip"] == "10.0.0.1"
    assert pods[0]["node"] == "node-1"
    assert len(pods[0]["containers"]) == 1
    assert pods[0]["containers"][0]["name"] == "container-1"

@pytest.mark.asyncio
async def test_create_job_success(k8s_client, mock_k8s_apis):
    """Test successful job creation."""
    name = "test-job"
    image = "test:latest"
    command = ["python", "test.py"]
    env_vars = {"KEY": "value"}
    cpu_limit = "100m"
    memory_limit = "256Mi"
    
    result = await k8s_client.create_job(
        name=name,
        image=image,
        command=command,
        env_vars=env_vars,
        cpu_limit=cpu_limit,
        memory_limit=memory_limit
    )
    
    assert result is True
    mock_k8s_apis["batch_v1"].create_namespaced_job.assert_called_once()
    call_args = mock_k8s_apis["batch_v1"].create_namespaced_job.call_args
    assert call_args[1]["namespace"] == "cahoots"
    
    job = call_args[1]["body"]
    assert job.metadata.name == name
    container = job.spec.template.spec.containers[0]
    assert container.image == image
    assert container.command == command
    assert container.env[0].name == "KEY"
    assert container.env[0].value == "value"
    assert container.resources.limits["cpu"] == cpu_limit
    assert container.resources.limits["memory"] == memory_limit

@pytest.mark.asyncio
async def test_delete_job_success(k8s_client, mock_k8s_apis):
    """Test successful job deletion."""
    name = "test-job"
    
    result = await k8s_client.delete_job(name)
    
    assert result is True
    mock_k8s_apis["batch_v1"].delete_namespaced_job.assert_called_once_with(
        name=name,
        namespace="cahoots",
        body=client.V1DeleteOptions(propagation_policy="Background")
    )

@pytest.mark.asyncio
async def test_delete_job_not_found(k8s_client, mock_k8s_apis):
    """Test job deletion when job not found."""
    mock_k8s_apis["batch_v1"].delete_namespaced_job.side_effect = \
        ApiException(status=404)
        
    result = await k8s_client.delete_job("test-job")
    
    assert result is True  # Should return True when job already deleted

def test_get_k8s_client():
    """Test global client instance creation."""
    with patch("packages.core.src.utils.infrastructure.k8s.client.KubernetesClient") as mock_client:
        client1 = get_k8s_client()
        client2 = get_k8s_client()
        
        # Should create only one instance
        mock_client.assert_called_once()
        assert client1 == client2 