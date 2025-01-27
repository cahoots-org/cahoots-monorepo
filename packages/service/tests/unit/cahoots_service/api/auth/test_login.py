"""Unit tests for login.py."""
import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, Mock, patch
from cahoots_service.api.auth.login import login, LoginRequest
from cahoots_service.schemas.auth import TokenResponse
from cahoots_service.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_login_success():
    """Test successful login."""
    # Arrange
    request = LoginRequest(email="test@example.com", password="password123")
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.settings = Mock()
    mock_auth_service.settings.access_token_expire_minutes = 30
    mock_auth_service.authenticate_user = AsyncMock(
        return_value=("test_user", "test_access_token", "test_refresh_token")
    )
    
    with patch("cahoots_service.api.auth.login.AuthService", return_value=mock_auth_service):
        # Act
        result = await login(request, mock_db)
        
        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.token_type == "bearer"
        assert result.expires_in == 1800  # 30 minutes * 60 seconds
        mock_auth_service.authenticate_user.assert_awaited_once_with(
            email="test@example.com", password="password123"
        )

@pytest.mark.asyncio
async def test_login_generic_error():
    """Test login with a generic error."""
    # Arrange
    request = LoginRequest(email="test@example.com", password="password123")
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.authenticate_user = AsyncMock(side_effect=Exception("DB error"))
    
    with patch("cahoots_service.api.auth.login.AuthService", return_value=mock_auth_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login(request, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_auth_service.authenticate_user.assert_awaited_once_with(
            email="test@example.com", password="password123"
        )

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.authenticate_user = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    )
    
    with patch('cahoots_service.api.auth.login.AuthService', return_value=mock_auth_service):
        request = LoginRequest(email="test@example.com", password="wrong-password")
        
        with pytest.raises(HTTPException) as exc:
            await login(request, mock_db)
            
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid credentials"
        
        mock_auth_service.authenticate_user.assert_awaited_once_with(
            email="test@example.com",
            password="wrong-password"
        )

@pytest.mark.asyncio
async def test_login_internal_error():
    """Test login with internal server error."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.authenticate_user = AsyncMock(
        side_effect=Exception("Database connection error")
    )
    
    with patch('cahoots_service.api.auth.login.AuthService', return_value=mock_auth_service):
        request = LoginRequest(email="test@example.com", password="password123")
        
        with pytest.raises(HTTPException) as exc:
            await login(request, mock_db)
            
        assert exc.value.status_code == 500
        assert exc.value.detail == "Database connection error"
        
        mock_auth_service.authenticate_user.assert_awaited_once_with(
            email="test@example.com",
            password="password123"
        ) 