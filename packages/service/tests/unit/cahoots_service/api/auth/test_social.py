"""Unit tests for social.py."""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from cahoots_service.api.auth.social import social_auth
from cahoots_service.schemas.auth import SocialAuthRequest, TokenResponse

# Mock environment variables for AuthService
TEST_ENV = {
    'SECRET_KEY': 'test-secret',
    'GOOGLE_CLIENT_ID': 'test-google-id',
    'GOOGLE_CLIENT_SECRET': 'test-google-secret',
    'GITHUB_CLIENT_ID': 'test-github-id',
    'GITHUB_CLIENT_SECRET': 'test-github-secret'
}

@pytest.mark.asyncio
@patch.dict('os.environ', TEST_ENV)
async def test_social_auth_google_success():
    """Test successful Google social authentication."""
    # Arrange
    provider = "google"
    request = SocialAuthRequest(
        token="google-token",
        provider_user_id="google-123",
        provider_data={"email": "test@gmail.com"}
    )
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.settings = Mock()
    mock_auth_service.settings.access_token_expire_minutes = 30
    mock_auth_service.authenticate_social = AsyncMock(
        return_value=("test_user", "test_access_token", "test_refresh_token")
    )
    
    with patch("cahoots_service.api.auth.social.AuthService", return_value=mock_auth_service):
        # Act
        result = await social_auth(provider, request, mock_db)
        
        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.token_type == "bearer"
        assert result.expires_in == 1800  # 30 minutes * 60 seconds
        mock_auth_service.authenticate_social.assert_awaited_once_with(
            provider="google",
            token="google-token",
            provider_user_id="google-123",
            provider_data={"email": "test@gmail.com"}
        )

@pytest.mark.asyncio
@patch.dict('os.environ', TEST_ENV)
async def test_social_auth_github_success():
    """Test successful GitHub social authentication."""
    # Arrange
    provider = "github"
    request = SocialAuthRequest(
        token="github-token",
        provider_user_id="github-123",
        provider_data={"login": "testuser"}
    )
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.settings = Mock()
    mock_auth_service.settings.access_token_expire_minutes = 30
    mock_auth_service.authenticate_social = AsyncMock(
        return_value=("test_user", "test_access_token", "test_refresh_token")
    )
    
    with patch("cahoots_service.api.auth.social.AuthService", return_value=mock_auth_service):
        # Act
        result = await social_auth(provider, request, mock_db)
        
        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.token_type == "bearer"
        assert result.expires_in == 1800  # 30 minutes * 60 seconds
        mock_auth_service.authenticate_social.assert_awaited_once_with(
            provider="github",
            token="github-token",
            provider_user_id="github-123",
            provider_data={"login": "testuser"}
        )

@pytest.mark.asyncio
@patch.dict('os.environ', TEST_ENV)
async def test_social_auth_unsupported_provider():
    """Test social auth with unsupported provider."""
    # Arrange
    provider = "facebook"
    request = SocialAuthRequest(
        token="fb-token",
        provider_user_id="fb-123",
        provider_data={}
    )
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    
    with patch("cahoots_service.api.auth.social.AuthService", return_value=mock_auth_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await social_auth(provider, request, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc_info.value.detail == "Unsupported provider: facebook"
        mock_auth_service.authenticate_social.assert_not_called()

@pytest.mark.asyncio
@patch.dict('os.environ', TEST_ENV)
async def test_social_auth_service_error():
    """Test social auth with service error."""
    # Arrange
    provider = "google"
    request = SocialAuthRequest(
        token="google-token",
        provider_user_id="google-123",
        provider_data={"email": "test@gmail.com"}
    )
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.authenticate_social = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    )
    
    with patch("cahoots_service.api.auth.social.AuthService", return_value=mock_auth_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await social_auth(provider, request, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid token"
        mock_auth_service.authenticate_social.assert_awaited_once_with(
            provider="google",
            token="google-token",
            provider_user_id="google-123",
            provider_data={"email": "test@gmail.com"}
        )

@pytest.mark.asyncio
@patch.dict('os.environ', TEST_ENV)
async def test_social_auth_generic_error():
    """Test social auth with generic error."""
    # Arrange
    provider = "google"
    request = SocialAuthRequest(
        token="google-token",
        provider_user_id="google-123",
        provider_data={"email": "test@gmail.com"}
    )
    mock_db = AsyncMock()
    mock_auth_service = Mock()
    mock_auth_service.authenticate_social = AsyncMock(
        side_effect=Exception("Internal error")
    )
    
    with patch("cahoots_service.api.auth.social.AuthService", return_value=mock_auth_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await social_auth(provider, request, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_auth_service.authenticate_social.assert_awaited_once_with(
            provider="google",
            token="google-token",
            provider_user_id="google-123",
            provider_data={"email": "test@gmail.com"}
        ) 