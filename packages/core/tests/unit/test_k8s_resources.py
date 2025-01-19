"""Unit tests for Kubernetes project resources."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from cahoots_core.utils.infrastructure.k8s.resources import ProjectResources, create_common_labels
from cahoots_core.utils.infrastructure import KubernetesClient

@pytest.fixture
def mock_k8s_client():
    """Create mock Kubernetes client."""
    client = AsyncMock(spec=KubernetesClient)
    client.create_namespace = AsyncMock()
    client.create_resource_quota = AsyncMock()
    client.create_limit_range = AsyncMock()
    client.create_network_policy = AsyncMock()
    client.create_service_account = AsyncMock()
    client.delete_namespace = AsyncMock()
    return client

@pytest.fixture
def project_resources(mock_k8s_client):
    """Create project resources instance."""
    project_id = str(uuid4())
    return ProjectResources(project_id=project_id, k8s_client=mock_k8s_client)

@pytest.mark.asyncio
async def test_setup_namespace(project_resources, mock_k8s_client):
    """Test namespace setup."""
    # When
    await project_resources.setup_namespace()

    # Then
    mock_k8s_client.create_namespace.assert_called_once_with(
        name=f"project-{project_resources.project_id}",
        labels={
            "project": project_resources.project_id,
            "managed-by": "cahoots"
        }
    )

@pytest.mark.asyncio
async def test_apply_resource_quotas(project_resources, mock_k8s_client):
    """Test applying resource quotas."""
    # Given
    quotas = {
        "requests.cpu": "4",
        "requests.memory": "8Gi",
        "limits.cpu": "8",
        "limits.memory": "16Gi",
        "pods": "20"
    }

    # When
    await project_resources.apply_resource_quotas(quotas)

    # Then
    mock_k8s_client.create_resource_quota.assert_called_once_with(
        namespace=f"project-{project_resources.project_id}",
        name=f"project-{project_resources.project_id}-quota",
        spec={"hard": quotas}
    )

@pytest.mark.asyncio
async def test_apply_limit_range(project_resources, mock_k8s_client):
    """Test applying limit ranges."""
    # Given
    limits = {
        "default": {
            "cpu": "200m",
            "memory": "512Mi"
        },
        "defaultRequest": {
            "cpu": "100m",
            "memory": "256Mi"
        },
        "max": {
            "cpu": "2",
            "memory": "4Gi"
        }
    }

    # When
    await project_resources.apply_limit_range(limits)

    # Then
    mock_k8s_client.create_limit_range.assert_called_once_with(
        namespace=f"project-{project_resources.project_id}",
        name=f"project-{project_resources.project_id}-limits",
        spec={
            "limits": [{
                "type": "Container",
                "default": limits["default"],
                "defaultRequest": limits["defaultRequest"],
                "max": limits["max"],
                "min": {}
            }]
        }
    )

@pytest.mark.asyncio
async def test_setup_network_policies(project_resources, mock_k8s_client):
    """Test setting up network policies."""
    # When
    await project_resources.setup_network_policies()

    # Then
    mock_k8s_client.create_network_policy.assert_called_once_with(
        namespace=f"project-{project_resources.project_id}",
        name=f"project-{project_resources.project_id}-isolation",
        spec={
            "podSelector": {},
            "policyTypes": ["Ingress", "Egress"],
            "ingress": [{
                "from": [{
                    "namespaceSelector": {
                        "matchLabels": {
                            "project": project_resources.project_id
                        }
                    }
                }]
            }],
            "egress": [{
                "to": [{
                    "namespaceSelector": {
                        "matchLabels": {
                            "project": project_resources.project_id
                        }
                    }
                }]
            }]
        }
    )

@pytest.mark.asyncio
async def test_setup_service_account(project_resources, mock_k8s_client):
    """Test setting up service account."""
    # When
    await project_resources.setup_service_account()

    # Then
    mock_k8s_client.create_service_account.assert_called_once_with(
        namespace=f"project-{project_resources.project_id}",
        name=f"project-{project_resources.project_id}-sa",
        labels={
            "project": project_resources.project_id
        }
    )

@pytest.mark.asyncio
async def test_initialize(project_resources, mock_k8s_client):
    """Test complete initialization."""
    # Given
    resource_limits = {
        "requests.cpu": "4",
        "requests.memory": "8Gi"
    }

    # When
    await project_resources.initialize(resource_limits)

    # Then
    mock_k8s_client.create_namespace.assert_called_once()
    mock_k8s_client.create_resource_quota.assert_called_once()
    mock_k8s_client.create_limit_range.assert_called_once()
    mock_k8s_client.create_network_policy.assert_called_once()
    mock_k8s_client.create_service_account.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup(project_resources, mock_k8s_client):
    """Test resource cleanup."""
    # When
    await project_resources.cleanup()

    # Then
    mock_k8s_client.delete_namespace.assert_called_once_with(
        f"project-{project_resources.project_id}"
    )

def test_create_common_labels():
    """Test creating common labels."""
    # Given
    name = "test-app"
    component = "api"

    # When
    labels = create_common_labels(name, component)

    # Then
    assert labels == {
        "app.kubernetes.io/name": name,
        "app.kubernetes.io/component": component,
        "app.kubernetes.io/managed-by": "cahoots"
    } 