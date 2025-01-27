"""Unit tests for auth module."""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, Mock
from cahoots_service.api.auth.verify import verify_api_key, get_current_user

@pytest.mark.asyncio
async def test_verify_api_key_success():
    """Test successful API key verification."""
    # Setup
    mock_security = AsyncMock()
    mock_security.authenticate.return_value = {"org_id": "test-org"}
    
    # Execute
    result = await verify_api_key("test-key", mock_security)
    
    # Assert
    assert result == "test-org"
    mock_security.authenticate.assert_awaited_once_with("test-key")

@pytest.mark.asyncio
async def test_verify_api_key_missing():
    """Test missing API key."""
    # Setup
    mock_security = AsyncMock()
    
    # Execute and Assert
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(None, mock_security)
    assert exc.value.status_code == 403
    assert exc.value.detail == "API key required"
    mock_security.authenticate.assert_not_called()

@pytest.mark.asyncio
async def test_verify_api_key_health():
    """Test health endpoint bypassing verification."""
    # Setup
    mock_security = AsyncMock()
    
    # Execute
    result = await verify_api_key("test-key", mock_security, "/api/v1/health")
    
    # Assert
    assert result is None
    mock_security.authenticate.assert_not_called()

@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test successful user retrieval."""
    # Setup
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(return_value={"user_id": "test-user"})
    
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_result = Mock()
    mock_result.scalar_one_or_none = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Execute
    result = await get_current_user("test-key", mock_security, mock_db)
    
    # Assert
    assert result.id == "test-user"
    assert result.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_current_user_not_found():
    """Test user not found."""
    # Setup
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(return_value={"user_id": "test-user"})
    
    mock_result = Mock()
    mock_result.scalar_one_or_none = None
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Execute and Assert
    with pytest.raises(HTTPException) as exc:
        await get_current_user("test-key", mock_security, mock_db)
    
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"