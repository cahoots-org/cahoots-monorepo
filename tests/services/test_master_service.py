import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.models.team_config import ServiceRole, RoleConfig
from src.services.master_service import MasterService
from src.core.dependencies import ServiceDeps

@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    deps = MagicMock(spec=ServiceDeps)
    deps.redis = AsyncMock()
    deps.context = AsyncMock()
    deps.db = AsyncMock()
    deps.db.execute = AsyncMock()
    deps.db.commit = AsyncMock()
    deps.db.rollback = AsyncMock()
    deps.db.close = AsyncMock()
    deps.k8s = AsyncMock()
    return deps

@pytest.fixture
def master_service(mock_deps):
    """Create master service with mock dependencies."""
    return MasterService(deps=mock_deps, project_id="test-project")

@pytest.mark.asyncio
async def test_get_role_instances(master_service, mock_deps):
    """Test getting role instances."""
    # Setup
    mock_deps.redis.get.return_value = "2"
    role = ServiceRole.DEVELOPER
    
    # Test
    instances = await master_service._get_role_instances(role)
    
    # Assert
    assert len(instances) == 2
    assert all(i.startswith(f"{role}-") for i in instances)
    mock_deps.redis.get.assert_called_once_with(f"scale:test-project:{role}")

@pytest.mark.asyncio
async def test_get_role_instances_default(master_service, mock_deps):
    """Test getting role instances with default count."""
    # Setup
    mock_deps.redis.get.return_value = None
    role = ServiceRole.DEVELOPER
    
    # Test
    instances = await master_service._get_role_instances(role)
    
    # Assert
    assert len(instances) == 1
    assert instances[0] == f"{role}-0"

@pytest.mark.asyncio
async def test_process_role(master_service, mock_deps):
    """Test processing a role."""
    # Setup
    role = ServiceRole.DEVELOPER
    instances = [f"{role}-0", f"{role}-1"]
    context = {"test": "data"}
    role_config = RoleConfig(enabled=True, tier="basic", context_priority=1)
    
    # Test
    result = await master_service._process_role(role, instances, context, role_config)
    
    # Assert
    assert result["instance"] in instances
    assert result["tier"] == "basic"
    assert result["status"] == "completed"
    assert result["results"]["role"] == role

@pytest.mark.asyncio
async def test_process_role_error(master_service, mock_deps):
    """Test error handling in process role."""
    # Setup
    role = ServiceRole.DEVELOPER
    instances = []  # Empty list will cause division by zero
    context = {"test": "data"}
    role_config = RoleConfig(enabled=True, tier="basic", context_priority=1)
    
    # Test & Assert
    with pytest.raises(HTTPException) as exc_info:
        await master_service._process_role(role, instances, context, role_config)
    assert exc_info.value.status_code == 500
    assert "Error processing request with" in exc_info.value.detail
    assert "integer modulo by zero" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_processing_order(master_service):
    """Test getting processing order."""
    # Test
    order = master_service._get_processing_order("feature_implementation")
    
    # Assert
    assert ServiceRole.PROJECT_MANAGER in order
    assert ServiceRole.DEVELOPER in order
    assert ServiceRole.QA_TESTER in order
    assert ServiceRole.UX_DESIGNER in order 