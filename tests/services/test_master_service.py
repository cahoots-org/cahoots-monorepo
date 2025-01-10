import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from src.models.team_config import ServiceRole, RoleConfig
from src.services.master_service import MasterService

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def mock_context():
    return AsyncMock()

@pytest.fixture
def master_service(mock_redis, mock_context):
    return MasterService(project_id="test-project", redis=mock_redis, context=mock_context)

@pytest.mark.asyncio
async def test_get_role_instances(master_service, mock_redis):
    """Test getting role instances."""
    # Setup
    mock_redis.get.return_value = "2"
    role = ServiceRole.DEVELOPER
    
    # Test
    instances = await master_service._get_role_instances(role)
    
    # Assert
    assert len(instances) == 2
    assert all(i.startswith(f"{role}-") for i in instances)
    mock_redis.get.assert_called_once_with(f"scale:test-project:{role}")

@pytest.mark.asyncio
async def test_get_role_instances_default(master_service, mock_redis):
    """Test getting role instances with default count."""
    # Setup
    mock_redis.get.return_value = None
    role = ServiceRole.DEVELOPER
    
    # Test
    instances = await master_service._get_role_instances(role)
    
    # Assert
    assert len(instances) == 1
    assert instances[0] == f"{role}-0"

@pytest.mark.asyncio
async def test_get_processing_order(master_service):
    """Test getting processing order for different request types."""
    # Test feature implementation order
    order = master_service._get_processing_order("feature_implementation")
    assert order == [
        ServiceRole.PROJECT_MANAGER,
        ServiceRole.DEVELOPER,
        ServiceRole.UX_DESIGNER,
        ServiceRole.QA_TESTER
    ]
    
    # Test code review order
    order = master_service._get_processing_order("code_review")
    assert order == [
        ServiceRole.DEVELOPER,
        ServiceRole.QA_TESTER
    ]
    
    # Test UI design order
    order = master_service._get_processing_order("ui_design")
    assert order == [
        ServiceRole.UX_DESIGNER,
        ServiceRole.DEVELOPER
    ]
    
    # Test unknown request type
    order = master_service._get_processing_order("unknown_type")
    assert order == []

@pytest.mark.asyncio
async def test_process_role(master_service):
    """Test processing a request through a role."""
    # Setup
    role = ServiceRole.DEVELOPER
    instances = [f"{role}-0", f"{role}-1"]
    context = {"key": "value"}
    role_config = RoleConfig(instances=2)
    
    # Test
    result = await master_service._process_role(role, instances, context, role_config)
    
    # Assert
    assert result["instance"] in instances
    assert result["tier"] == role_config.tier
    assert result["status"] == "completed"
    assert result["results"]["role"] == role
    assert result["results"]["context_size"] == len(str(context))

@pytest.mark.asyncio
async def test_process_role_error(master_service):
    """Test error handling in role processing."""
    # Setup
    role = ServiceRole.DEVELOPER
    instances = []  # Empty instance list to trigger error
    context = {"key": "value"}
    role_config = RoleConfig(instances=1)
    
    # Test & Assert
    with pytest.raises(HTTPException) as exc:
        await master_service._process_role(role, instances, context, role_config)
    assert exc.value.status_code == 500
    assert "Error processing request" in str(exc.value.detail) 