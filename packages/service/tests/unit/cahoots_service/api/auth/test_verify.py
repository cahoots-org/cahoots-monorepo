"""Unit tests for verify.py."""
import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, Mock
from cahoots_service.api.auth.verify import verify_api_key, get_current_user, verify_email, resend_verification
from cahoots_service.schemas.auth import EmailVerificationRequest, ResendVerificationRequest

@pytest.mark.asyncio
async def test_verify_api_key_success():
    """Test successful API key verification."""
    mock_request = Mock()
    mock_request.url.path = "/api/v1/test"
    
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(return_value={"organization_id": "test-org"})
    
    result = await verify_api_key(mock_request, "test-key", mock_security)
    assert result == "test-org"

@pytest.mark.asyncio
async def test_verify_api_key_missing():
    """Test missing API key."""
    mock_request = Mock()
    mock_request.url.path = "/api/v1/test"
    
    mock_security = Mock()
    
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(mock_request, None, mock_security)
    assert exc.value.status_code == 403
    assert exc.value.detail == "API key required"

@pytest.mark.asyncio
async def test_verify_api_key_invalid():
    """Test invalid API key."""
    mock_request = Mock()
    mock_request.url.path = "/api/v1/test"
    
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(side_effect=HTTPException(status_code=403, detail="Invalid API key"))
    
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(mock_request, "invalid-key", mock_security)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Invalid API key"

@pytest.mark.asyncio
async def test_verify_api_key_health():
    """Test health endpoint bypassing verification."""
    mock_request = Mock()
    mock_request.url.path = "/health"
    
    mock_security = Mock()
    
    result = await verify_api_key(mock_request, None, mock_security)
    assert result == "test-org"

@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test successful user retrieval."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(return_value={"user_id": "test-user"})
    
    result = await get_current_user("test-key", mock_security, mock_db)
    assert result.id == "test-user"
    assert result.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_current_user_not_found():
    """Test user not found."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_security = Mock()
    mock_security.authenticate = AsyncMock(return_value={"user_id": "test-user"})
    
    with pytest.raises(HTTPException) as exc:
        await get_current_user("test-key", mock_security, mock_db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"

@pytest.mark.asyncio
async def test_verify_email_success():
    """Test successful email verification."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    mock_user.full_name = "Test User"
    mock_user.is_verified = False
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    mock_security = Mock()
    mock_security.verify_email = AsyncMock(return_value="test-user")
    
    mock_email = Mock()
    mock_email.send_welcome_email = AsyncMock()
    
    request = EmailVerificationRequest(token="test-token")
    result = await verify_email(request, mock_security, mock_db, mock_email)
    
    assert result == {"message": "Email verified successfully"}
    assert mock_user.is_verified is True
    mock_db.commit.assert_awaited_once()
    mock_email.send_welcome_email.assert_awaited_once_with(
        email="test@example.com",
        name="Test User"
    )

@pytest.mark.asyncio
async def test_verify_email_user_not_found():
    """Test email verification when user not found."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.rollback = AsyncMock()
    
    mock_security = Mock()
    mock_security.verify_email = AsyncMock(return_value="test-user")
    
    mock_email = Mock()
    
    request = EmailVerificationRequest(token="test-token")
    with pytest.raises(HTTPException) as exc:
        await verify_email(request, mock_security, mock_db, mock_email)
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"

@pytest.mark.asyncio
async def test_verify_email_already_verified():
    """Test email verification when already verified."""
    mock_user = Mock()
    mock_user.is_verified = True
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.rollback = AsyncMock()
    
    mock_security = Mock()
    mock_security.verify_email = AsyncMock(return_value="test-user")
    
    mock_email = Mock()
    
    request = EmailVerificationRequest(token="test-token")
    with pytest.raises(HTTPException) as exc:
        await verify_email(request, mock_security, mock_db, mock_email)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already verified"

@pytest.mark.asyncio
async def test_verify_email_db_error():
    """Test email verification when DB error occurs."""
    mock_user = Mock()
    mock_user.is_verified = False
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock(side_effect=Exception("DB error"))
    mock_db.rollback = AsyncMock()
    
    mock_security = Mock()
    mock_security.verify_email = AsyncMock(return_value="test-user")
    
    mock_email = Mock()
    
    request = EmailVerificationRequest(token="test-token")
    with pytest.raises(HTTPException) as exc:
        await verify_email(request, mock_security, mock_db, mock_email)
    assert exc.value.status_code == 500
    assert exc.value.detail == "DB error"
    mock_db.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_resend_verification_success():
    """Test successful verification email resend."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_security = Mock()
    mock_security.create_verification_token = AsyncMock(return_value="new-token")
    
    mock_email = Mock()
    mock_email.send_verification_email = AsyncMock()
    
    request = ResendVerificationRequest(user_id="test-user")
    await resend_verification(request, mock_security, mock_db, mock_email)
    
    mock_security.create_verification_token.assert_awaited_once_with("test-user")
    mock_email.send_verification_email.assert_awaited_once_with(
        email="test@example.com",
        token="new-token"
    )

@pytest.mark.asyncio
async def test_resend_verification_user_not_found():
    """Test verification email resend when user not found."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_security = Mock()
    mock_email = Mock()
    
    request = ResendVerificationRequest(user_id="test-user")
    with pytest.raises(HTTPException) as exc:
        await resend_verification(request, mock_security, mock_db, mock_email)
    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"

@pytest.mark.asyncio
async def test_resend_verification_error():
    """Test verification email resend when error occurs."""
    mock_user = Mock()
    mock_user.id = "test-user"
    mock_user.email = "test@example.com"
    
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_user
    
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_security = Mock()
    mock_security.create_verification_token = AsyncMock(side_effect=Exception("Token error"))
    
    mock_email = Mock()
    
    request = ResendVerificationRequest(user_id="test-user")
    with pytest.raises(HTTPException) as exc:
        await resend_verification(request, mock_security, mock_db, mock_email)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Token error"
