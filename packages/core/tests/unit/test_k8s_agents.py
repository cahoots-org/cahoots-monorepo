"""Unit tests for Kubernetes agent deployment."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from cahoots_core.utils.infrastructure.k8s.agents import AgentDeployment
from cahoots_core.utils.infrastructure import KubernetesClient

@pytest.fixture
def mock_k8s_client():
    """Create mock Kubernetes client."""
    client = AsyncMock(spec=KubernetesClient)
    client.create_deployment = AsyncMock()
    client.scale_deployment = AsyncMock()
    client.delete_deployment = AsyncMock()
    client.get_deployment_status = AsyncMock()
    return client

@pytest.fixture
def agent_deployment(mock_k8s_client):
    """Create agent deployment instance."""
    project_id = str(uuid4())
    return AgentDeployment(project_id=project_id, k8s_client=mock_k8s_client)

@pytest.mark.asyncio
async def test_deploy_agent(agent_deployment, mock_k8s_client):
    """Test agent deployment creation."""
    # Given
    agent_type = "developer"
    config = {"key": "value"}
    tier = "premium"

    # When
    await agent_deployment.deploy_agent(agent_type, config, tier)

    # Then
    mock_k8s_client.create_deployment.assert_called_once()
    deployment = mock_k8s_client.create_deployment.call_args[0][0]

    # Verify deployment spec
    assert deployment["kind"] == "Deployment"
    assert deployment["metadata"]["namespace"] == f"project-{agent_deployment.project_id}"
    assert deployment["metadata"]["labels"]["agent-type"] == agent_type
    
    # Verify container spec
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["name"] == agent_type
    assert container["image"] == f"cahoots/agent-{agent_type}:latest"
    
    # Verify environment variables
    env_vars = {e["name"]: e["value"] for e in container["env"]}
    assert env_vars["PROJECT_ID"] == agent_deployment.project_id
    assert env_vars["AGENT_TYPE"] == agent_type
    assert env_vars["CONFIG"] == str(config)
    
    # Verify resource requirements for premium tier
    resources = container["resources"]
    assert resources["requests"]["cpu"] == "200m"
    assert resources["requests"]["memory"] == "512Mi"
    assert resources["limits"]["cpu"] == "500m"
    assert resources["limits"]["memory"] == "1Gi"

@pytest.mark.asyncio
async def test_scale_agent(agent_deployment, mock_k8s_client):
    """Test agent scaling."""
    # Given
    agent_type = "qa"
    replicas = 3

    # When
    await agent_deployment.scale_agent(agent_type, replicas)

    # Then
    mock_k8s_client.scale_deployment.assert_called_once_with(
        name=f"{agent_type}-{agent_deployment.project_id}",
        namespace=f"project-{agent_deployment.project_id}",
        replicas=replicas
    )

@pytest.mark.asyncio
async def test_delete_agent(agent_deployment, mock_k8s_client):
    """Test agent deletion."""
    # Given
    agent_type = "developer"

    # When
    await agent_deployment.delete_agent(agent_type)

    # Then
    mock_k8s_client.delete_deployment.assert_called_once_with(
        name=f"{agent_type}-{agent_deployment.project_id}",
        namespace=f"project-{agent_deployment.project_id}"
    )

@pytest.mark.asyncio
async def test_get_agent_status(agent_deployment, mock_k8s_client):
    """Test getting agent status."""
    # Given
    agent_type = "developer"
    mock_status = {"replicas": 1, "ready_replicas": 1}
    mock_k8s_client.get_deployment_status.return_value = mock_status

    # When
    status = await agent_deployment.get_agent_status(agent_type)

    # Then
    assert status == mock_status
    mock_k8s_client.get_deployment_status.assert_called_once_with(
        name=f"{agent_type}-{agent_deployment.project_id}",
        namespace=f"project-{agent_deployment.project_id}"
    )

@pytest.mark.asyncio
async def test_agent_env_variables(agent_deployment):
    """Test environment variable generation."""
    # Given
    agent_type = "developer"
    config = {"memory": "1Gi", "cpu": "500m"}

    # When
    env_vars = agent_deployment._get_agent_env(agent_type, config)

    # Then
    expected_vars = {
        "PROJECT_ID": agent_deployment.project_id,
        "AGENT_TYPE": agent_type,
        "REDIS_NAMESPACE": f"project:{agent_deployment.project_id}",
        "DB_SCHEMA": f"project_{agent_deployment.project_id}",
        "CONFIG": str(config)
    }

    assert len(env_vars) == len(expected_vars)
    for var in env_vars:
        assert var["name"] in expected_vars
        assert var["value"] == expected_vars[var["name"]]

@pytest.mark.asyncio
async def test_agent_resources_by_tier(agent_deployment):
    """Test resource allocation by tier."""
    tiers = ["basic", "premium", "enterprise"]
    expected_resources = {
        "basic": {
            "requests": {"cpu": "100m", "memory": "256Mi"},
            "limits": {"cpu": "200m", "memory": "512Mi"}
        },
        "premium": {
            "requests": {"cpu": "200m", "memory": "512Mi"},
            "limits": {"cpu": "500m", "memory": "1Gi"}
        },
        "enterprise": {
            "requests": {"cpu": "500m", "memory": "1Gi"},
            "limits": {"cpu": "1", "memory": "2Gi"}
        }
    }

    for tier in tiers:
        resources = agent_deployment._get_agent_resources(tier)
        assert resources == expected_resources[tier]

    # Test default to basic for unknown tier
    resources = agent_deployment._get_agent_resources("unknown")
    assert resources == expected_resources["basic"] 