"""Unit tests for register.py."""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from cahoots_service.api.auth.register import register, UserRegistration

@pytest.mark.asyncio
@patch('cahoots_service.api.auth.register.User')
async def test_register_success(mock_user_cls):
    """Test successful user registration."""
    # Arrange
    request = UserRegistration(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    mock_db = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_security = Mock()
    mock_security.get_user_by_email = AsyncMock(return_value=None)
    mock_security.hash_password = AsyncMock(return_value="hashed_password")
    mock_security.generate_verification_token = AsyncMock(return_value="test_token")
    mock_email = AsyncMock()
    mock_email.send_verification_email = AsyncMock()
    
    # Act
    result = await register(request, mock_security, mock_db, mock_email)
    
    # Assert
    assert result == {
        "message": "Registration successful. Please check your email to verify your account."
    }
    mock_security.get_user_by_email.assert_awaited_once_with("test@example.com")
    mock_security.hash_password.assert_awaited_once_with("password123")
    mock_security.generate_verification_token.assert_awaited_once()
    mock_user_cls.assert_called_once_with(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=False,
        verification_token="test_token"
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
    mock_email.send_verification_email.assert_awaited_once_with(
        email="test@example.com",
        token="test_token"
    )

@pytest.mark.asyncio
async def test_register_existing_email():
    """Test registration with existing email."""
    # Arrange
    request = UserRegistration(
        email="existing@example.com",
        password="password123",
        full_name="Test User"
    )
    mock_db = Mock()
    mock_security = Mock()
    mock_security.get_user_by_email = AsyncMock(return_value={"id": "123"})
    mock_email = AsyncMock()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await register(request, mock_security, mock_db, mock_email)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Email already registered"
    mock_security.get_user_by_email.assert_awaited_once_with("existing@example.com")
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
    mock_email.send_verification_email.assert_not_awaited()

@pytest.mark.asyncio
@patch('cahoots_service.api.auth.register.User')
async def test_register_db_error(mock_user_cls):
    """Test registration with database error."""
    # Arrange
    request = UserRegistration(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    mock_db = Mock()
    mock_db.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
    mock_db.rollback = AsyncMock()
    mock_security = Mock()
    mock_security.get_user_by_email = AsyncMock(return_value=None)
    mock_security.hash_password = AsyncMock(return_value="hashed_password")
    mock_security.generate_verification_token = AsyncMock(return_value="test_token")
    mock_email = AsyncMock()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await register(request, mock_security, mock_db, mock_email)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    mock_db.rollback.assert_awaited_once()
    mock_email.send_verification_email.assert_not_awaited()

@pytest.mark.asyncio
@patch('cahoots_service.api.auth.register.User')
async def test_register_email_error(mock_user_cls):
    """Test registration with email service error."""
    # Arrange
    request = UserRegistration(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    mock_db = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_security = Mock()
    mock_security.get_user_by_email = AsyncMock(return_value=None)
    mock_security.hash_password = AsyncMock(return_value="hashed_password")
    mock_security.generate_verification_token = AsyncMock(return_value="test_token")
    mock_email = AsyncMock()
    mock_email.send_verification_email = AsyncMock(side_effect=Exception("Email error"))
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await register(request, mock_security, mock_db, mock_email)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Email error"
    mock_db.rollback.assert_awaited_once()
    # Don't assert email was sent since it should fail 