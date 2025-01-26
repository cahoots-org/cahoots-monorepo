"""Unit tests for password.py."""
import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, Mock, patch
from cahoots_service.api.auth.password import (
    change_password,
    forgot_password,
    reset_password,
    PasswordResetRequest,
    PasswordReset
)
from cahoots_service.schemas.auth import PasswordChangeRequest
from cahoots_service.services.auth_service import AuthService
from cahoots_service.services.email_service import EmailService

@pytest.mark.asyncio
async def test_change_password_success():
    """Test successful password change."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.change_password = AsyncMock()
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordChangeRequest(
            current_password="old-password",
            new_password="new-password"
        )
        await change_password(request, mock_user, mock_db)
        
        mock_auth_service.change_password.assert_awaited_once_with(
            user=mock_user,
            current_password="old-password",
            new_password="new-password"
        )

@pytest.mark.asyncio
async def test_change_password_invalid_current():
    """Test password change with invalid current password."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.change_password = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password"
        )
    )
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordChangeRequest(
            current_password="wrong-password",
            new_password="new-password"
        )
        
        with pytest.raises(HTTPException) as exc:
            await change_password(request, mock_user, mock_db)
            
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid current password"
        
        mock_auth_service.change_password.assert_awaited_once_with(
            user=mock_user,
            current_password="wrong-password",
            new_password="new-password"
        )

@pytest.mark.asyncio
async def test_change_password_error():
    """Test password change with internal error."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.change_password = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordChangeRequest(
            current_password="old-password",
            new_password="new-password"
        )
        
        with pytest.raises(HTTPException) as exc:
            await change_password(request, mock_user, mock_db)
            
        assert exc.value.status_code == 500
        assert exc.value.detail == "Database error"
        
        mock_auth_service.change_password.assert_awaited_once_with(
            user=mock_user,
            current_password="old-password",
            new_password="new-password"
        )

@pytest.mark.asyncio
async def test_forgot_password_success():
    """Test successful password reset request."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.create_password_reset = AsyncMock(
        return_value=(mock_user, "reset-token")
    )
    
    mock_email_service = Mock()
    mock_email_service.send_password_reset_email = AsyncMock()
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service), \
         patch('cahoots_service.api.auth.password.EmailService', return_value=mock_email_service):
        request = PasswordResetRequest(email="test@example.com")
        await forgot_password(request, mock_db)
        
        mock_auth_service.create_password_reset.assert_awaited_once_with(
            email="test@example.com"
        )
        mock_email_service.send_password_reset_email.assert_awaited_once_with(
            email="test@example.com",
            token="reset-token"
        )

@pytest.mark.asyncio
async def test_forgot_password_user_not_found():
    """Test password reset request for non-existent user."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.create_password_reset = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    )
    
    mock_email_service = Mock()
    mock_email_service.send_password_reset_email = AsyncMock()
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service), \
         patch('cahoots_service.api.auth.password.EmailService', return_value=mock_email_service):
        request = PasswordResetRequest(email="nonexistent@example.com")
        
        with pytest.raises(HTTPException) as exc:
            await forgot_password(request, mock_db)
            
        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"
        
        mock_auth_service.create_password_reset.assert_awaited_once_with(
            email="nonexistent@example.com"
        )

@pytest.mark.asyncio
async def test_forgot_password_error():
    """Test password reset request with internal error."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.create_password_reset = AsyncMock(
        side_effect=Exception("Email service error")
    )
    
    mock_email_service = Mock()
    mock_email_service.send_password_reset_email = AsyncMock()
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service), \
         patch('cahoots_service.api.auth.password.EmailService', return_value=mock_email_service):
        request = PasswordResetRequest(email="test@example.com")
        
        with pytest.raises(HTTPException) as exc:
            await forgot_password(request, mock_db)
            
        assert exc.value.status_code == 500
        assert exc.value.detail == "Email service error"
        
        mock_auth_service.create_password_reset.assert_awaited_once_with(
            email="test@example.com"
        )

@pytest.mark.asyncio
async def test_reset_password_success():
    """Test successful password reset."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.reset_password = AsyncMock()
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordReset(
            token="reset-token",
            new_password="new-password"
        )
        await reset_password(request, mock_db)
        
        mock_auth_service.reset_password.assert_awaited_once_with(
            token="reset-token",
            new_password="new-password"
        )

@pytest.mark.asyncio
async def test_reset_password_invalid_token():
    """Test password reset with invalid token."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.reset_password = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    )
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordReset(
            token="invalid-token",
            new_password="new-password"
        )
        
        with pytest.raises(HTTPException) as exc:
            await reset_password(request, mock_db)
            
        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid or expired reset token"
        
        mock_auth_service.reset_password.assert_awaited_once_with(
            token="invalid-token",
            new_password="new-password"
        )

@pytest.mark.asyncio
async def test_reset_password_error():
    """Test password reset with internal error."""
    mock_db = AsyncMock()
    
    mock_auth_service = Mock()
    mock_auth_service.reset_password = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    with patch('cahoots_service.api.auth.password.AuthService', return_value=mock_auth_service):
        request = PasswordReset(
            token="reset-token",
            new_password="new-password"
        )
        
        with pytest.raises(HTTPException) as exc:
            await reset_password(request, mock_db)
            
        assert exc.value.status_code == 500
        assert exc.value.detail == "Database error"
        
        mock_auth_service.reset_password.assert_awaited_once_with(
            token="reset-token",
            new_password="new-password"
        ) 