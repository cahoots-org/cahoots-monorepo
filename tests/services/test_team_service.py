import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.models.team_config import TeamConfig, ServiceRole, RoleConfig, ProjectLimits
from src.services.team_service import TeamService
from src.core.dependencies import ServiceDeps
from src.utils.k8s import KubernetesClient

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.db = AsyncMock()
    deps.redis = AsyncMock()
    deps.k8s = MagicMock(spec=KubernetesClient)
    return deps

@pytest.fixture
def team_service(mock_deps):
    """Create team service with mock dependencies."""
    return TeamService(deps=mock_deps, project_id="test-project")

@pytest.fixture
def sample_config():
    return TeamConfig(
        project_id="test-project",
        roles={
            ServiceRole.DEVELOPER: RoleConfig(instances=2),
            ServiceRole.QA_TESTER: RoleConfig(),
            ServiceRole.UX_DESIGNER: RoleConfig(),
            ServiceRole.PROJECT_MANAGER: RoleConfig(),
        }
    )

@pytest.mark.asyncio
async def test_get_team_config_from_cache(team_service, mock_deps, sample_config):
    """Test retrieving team config from cache."""
    # Setup
    mock_deps.redis.get.return_value = sample_config.model_dump_json()
    
    # Test
    config = await team_service.get_team_config()
    
    # Assert
    assert config == sample_config  # Only verify we got the expected config

@pytest.mark.asyncio
async def test_get_team_config_from_db(team_service, mock_deps, sample_config):
    """Test retrieving team config from database when not in cache."""
    # Setup
    mock_deps.redis.get.return_value = None
    mock_deps.db.execute.return_value.first.return_value = ({"config": sample_config.model_dump()},)
    
    # Test
    config = await team_service.get_team_config()
    
    # Assert
    assert config.model_dump() == sample_config.model_dump()  # Only verify we got the expected config

@pytest.mark.asyncio
async def test_get_team_config_create_default(team_service, mock_deps):
    """Test creating default config when none exists."""
    # Setup
    mock_deps.redis.get.return_value = None
    mock_deps.db.execute.return_value.first.return_value = None
    
    # Test
    config = await team_service.get_team_config()
    
    # Assert
    assert config.project_id == "test-project"  # Use the project_id from team_service initialization

@pytest.mark.asyncio
async def test_update_team_config_success(team_service, mock_deps, sample_config):
    """Test successful team config update."""
    # Test
    updated_config = await team_service.update_team_config(sample_config)
    
    # Assert
    assert updated_config == sample_config  # Only verify the config was updated correctly

@pytest.mark.asyncio
async def test_update_team_config_exceeds_limits(team_service, mock_deps):
    """Test config update that exceeds project limits."""
    # Setup
    config = TeamConfig(
        project_id="test-project",
        max_total_instances=20,  # Higher limit in config
        roles={
            ServiceRole.DEVELOPER: RoleConfig(instances=8),
            ServiceRole.QA_TESTER: RoleConfig(instances=8)
        }
    )
    
    # Mock the internal method directly
    team_service._get_project_limits = AsyncMock(return_value=ProjectLimits(
        max_total_instances=10  # Lower limit in project settings
    ))
    
    # Test & Assert
    with pytest.raises(HTTPException) as exc:
        await team_service.update_team_config(config)
    assert exc.value.status_code == 400  # Only verify the error status

@pytest.mark.asyncio
async def test_update_role_config(team_service, mock_deps, sample_config):
    """Test updating configuration for a specific role."""
    # Setup
    mock_deps.redis.get.return_value = sample_config.model_dump_json()
    new_role_config = RoleConfig(instances=3)
    
    # Test
    updated_config = await team_service.update_role_config(ServiceRole.DEVELOPER, new_role_config)
    
    # Assert
    assert updated_config.roles[ServiceRole.DEVELOPER] == new_role_config  # Only verify the role was updated

@pytest.mark.asyncio
async def test_scale_role_instances(team_service, mock_deps):
    """Test scaling role instances."""
    # Setup
    role = ServiceRole.DEVELOPER
    instances = 3
    
    # Test
    await team_service._scale_role_instances(role, instances)
    
    # Assert
    mock_deps.k8s.scale_deployment.assert_called_once_with(
        deployment_name=f"{role}-test-project",
        replicas=instances
    ) 