"""Integration tests for complete project flow."""
import asyncio
import pytest
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ai_dev_team_service.utils.config import Settings
from ai_dev_team_service.schemas.projects import ProjectCreate, ProjectUpdate
from ai_dev_team_service.services.project_service import ProjectService
from ai_dev_team_service.services.metrics_service import MetricsService
from ai_dev_team_service.utils.infrastructure import (
    DatabaseManager,
    RedisManager,
    KubernetesClient,
    GitHubClient
)

@pytest.fixture
async def settings():
    """Test settings."""
    return Settings(
        api_base_url="http://test.local",
        github_token="test-token",
        agent_images={
            "developer": "ghcr.io/cahoots/developer-agent:latest"
        }
    )

@pytest.fixture
async def project_service(settings):
    """Test project service."""
    return ProjectService(
        settings=settings,
        db_manager=DatabaseManager(),
        redis_manager=RedisManager(),
        k8s_client=KubernetesClient(),
        github_client=GitHubClient()
    )

@pytest.fixture
async def metrics_service():
    """Test metrics service."""
    return MetricsService(
        db_session=AsyncSession(),
        db_manager=DatabaseManager(),
        redis_manager=RedisManager()
    )

@pytest.mark.integration
async def test_complete_project_flow(
    settings,
    project_service,
    metrics_service
):
    """Test complete project lifecycle."""
    # Create test data
    org_id = UUID()
    user_id = UUID()
    project_data = ProjectCreate(
        name="Test Project",
        description="Integration test project",
        agent_config={
            "developer": {
                "model": "gpt-4",
                "temperature": 0.7
            }
        },
        resource_limits={
            "cpu": "2",
            "memory": "4Gi",
            "pods": "5"
        }
    )
    
    # Create project
    project = await project_service.create_project(
        organization_id=org_id,
        project_data=project_data,
        user_id=user_id
    )
    
    assert project.id is not None
    assert project.status == "ready"
    assert project.progress == 100.0
    
    # Verify HATEOAS links
    assert project.links.self is not None
    assert project.links.github_repo is not None
    assert project.links.monitoring is not None
    assert project.links.logs is not None
    
    # Wait for resources to initialize
    await asyncio.sleep(5)
    
    # Verify Kubernetes resources
    k8s_client = KubernetesClient()
    namespace = f"project-{project.id}"
    
    # Check namespace exists
    ns = await k8s_client.get_namespace(namespace)
    assert ns is not None
    
    # Check resource quota
    quota = await k8s_client.get_resource_quota(namespace)
    assert quota.spec.hard["cpu"] == "2"
    assert quota.spec.hard["memory"] == "4Gi"
    
    # Check agent deployment
    deployment = await k8s_client.get_deployment(
        namespace=namespace,
        name="developer-agent"
    )
    assert deployment is not None
    assert deployment.spec.replicas == 1
    
    # Verify Redis namespace
    redis_client = RedisManager()
    redis_ns = f"project:{project.id}"
    
    keys = await redis_client.get_keys(redis_ns)
    assert len(keys) > 0
    
    # Verify database schema
    db_manager = DatabaseManager()
    schema = f"project_{project.id}"
    
    tables = await db_manager.get_tables(schema)
    assert len(tables) > 0
    
    # Collect and verify metrics
    await metrics_service.collect_metrics(project.id)
    metrics = await metrics_service.get_current_usage(project.id)
    
    assert metrics["k8s_pod_count"] > 0
    assert metrics["k8s_total_cpu_cores"] > 0
    assert metrics["k8s_total_memory_mb"] > 0
    assert metrics["redis_memory_bytes"] >= 0
    assert metrics["database_size_bytes"] > 0
    
    # Update project
    update_data = ProjectUpdate(
        name="Updated Test Project",
        agent_config={
            "developer": {
                "model": "gpt-4",
                "temperature": 0.5
            }
        }
    )
    
    updated = await project_service.update_project(
        project_id=project.id,
        update_data=update_data,
        user_id=user_id
    )
    
    assert updated.name == "Updated Test Project"
    assert updated.agent_config["developer"]["temperature"] == 0.5
    
    # Delete project
    deleted = await project_service.delete_project(
        project_id=project.id,
        user_id=user_id
    )
    
    assert deleted is True
    
    # Verify cleanup
    await asyncio.sleep(5)
    
    # Check Kubernetes cleanup
    ns = await k8s_client.get_namespace(namespace)
    assert ns is None
    
    # Check Redis cleanup
    keys = await redis_client.get_keys(redis_ns)
    assert len(keys) == 0
    
    # Check database cleanup
    tables = await db_manager.get_tables(schema)
    assert len(tables) == 0

@pytest.mark.integration
async def test_project_creation_failure(
    settings,
    project_service
):
    """Test project creation failure and cleanup."""
    org_id = UUID()
    user_id = UUID()
    
    # Create project with invalid resource limits
    project_data = ProjectCreate(
        name="Invalid Project",
        description="Should fail",
        resource_limits={
            "cpu": "-1",  # Invalid CPU value
            "memory": "4Gi"
        }
    )
    
    with pytest.raises(Exception):
        await project_service.create_project(
            organization_id=org_id,
            project_data=project_data,
            user_id=user_id
        )
    
    # Verify no resources were left behind
    k8s_client = KubernetesClient()
    namespaces = await k8s_client.list_namespaces(
        label_selector="resource-type=project"
    )
    
    for ns in namespaces:
        assert ns.metadata.labels.get("organization-id") != str(org_id)

@pytest.mark.integration
async def test_concurrent_projects(
    settings,
    project_service,
    metrics_service
):
    """Test creating multiple projects concurrently."""
    org_id = UUID()
    user_id = UUID()
    
    # Create multiple projects
    projects = []
    for i in range(3):
        project_data = ProjectCreate(
            name=f"Concurrent Project {i}",
            description=f"Test project {i}",
            resource_limits={
                "cpu": "1",
                "memory": "2Gi"
            }
        )
        
        projects.append(
            project_service.create_project(
                organization_id=org_id,
                project_data=project_data,
                user_id=user_id
            )
        )
    
    # Wait for all projects to complete
    results = await asyncio.gather(*projects)
    
    # Verify all projects
    for project in results:
        assert project.status == "ready"
        assert project.progress == 100.0
        
        # Check resources
        namespace = f"project-{project.id}"
        ns = await k8s_client.get_namespace(namespace)
        assert ns is not None
        
    # Collect metrics for all projects
    for project in results:
        await metrics_service.collect_metrics(project.id)
        metrics = await metrics_service.get_current_usage(project.id)
        assert metrics["k8s_pod_count"] > 0
        
    # Cleanup
    for project in results:
        await project_service.delete_project(
            project_id=project.id,
            user_id=user_id
        ) 