"""Unit tests for tokens.py."""
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, status

from cahoots_service.api.auth.tokens import refresh_token, logout
from cahoots_service.schemas.auth import RefreshTokenRequest, TokenResponse

@pytest.mark.asyncio
async def test_refresh_token_success():
    """Test successful token refresh."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="old-refresh-token")
    mock_security = Mock()
    mock_security.validate_token = AsyncMock(return_value={"sub": "test-user"})
    mock_security.create_tokens = AsyncMock(
        return_value=("new-access-token", "new-refresh-token")
    )
    mock_security.revoke_token = AsyncMock()
    mock_security.config = Mock()
    mock_security.config.access_token_expire_minutes = 30
    
    # Act
    result = await refresh_token(request, mock_security)
    
    # Assert
    assert isinstance(result, TokenResponse)
    assert result.access_token == "new-access-token"
    assert result.refresh_token == "new-refresh-token"
    assert result.token_type == "bearer"
    assert result.expires_in == 1800  # 30 minutes * 60 seconds
    mock_security.validate_token.assert_awaited_once_with("old-refresh-token")
    mock_security.create_tokens.assert_awaited_once_with("test-user")
    mock_security.revoke_token.assert_awaited_once_with("old-refresh-token")

@pytest.mark.asyncio
async def test_refresh_token_invalid():
    """Test refresh token with invalid token."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="invalid-token")
    mock_security = Mock()
    mock_security.validate_token = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(request, mock_security)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid refresh token"
    mock_security.validate_token.assert_awaited_once_with("invalid-token")
    mock_security.create_tokens.assert_not_called()
    mock_security.revoke_token.assert_not_called()

@pytest.mark.asyncio
async def test_refresh_token_error():
    """Test refresh token with generic error."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="test-token")
    mock_security = Mock()
    mock_security.validate_token = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(request, mock_security)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Database error"
    mock_security.validate_token.assert_awaited_once_with("test-token")
    mock_security.create_tokens.assert_not_called()
    mock_security.revoke_token.assert_not_called()

@pytest.mark.asyncio
async def test_logout_success():
    """Test successful logout."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="test-token")
    mock_security = Mock()
    mock_security.revoke_token = AsyncMock()
    
    # Act
    await logout(request, mock_security)
    
    # Assert
    mock_security.revoke_token.assert_awaited_once_with("test-token")

@pytest.mark.asyncio
async def test_logout_invalid_token():
    """Test logout with invalid token."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="invalid-token")
    mock_security = Mock()
    mock_security.revoke_token = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await logout(request, mock_security)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid refresh token"
    mock_security.revoke_token.assert_awaited_once_with("invalid-token")

@pytest.mark.asyncio
async def test_logout_error():
    """Test logout with generic error."""
    # Arrange
    request = RefreshTokenRequest(refresh_token="test-token")
    mock_security = Mock()
    mock_security.revoke_token = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await logout(request, mock_security)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Database error"
    mock_security.revoke_token.assert_awaited_once_with("test-token") 