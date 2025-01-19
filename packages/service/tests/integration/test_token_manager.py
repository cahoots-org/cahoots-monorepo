"""Integration tests for TokenManager."""
import pytest
import asyncio
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException

from src.utils.security import TokenManager
from src.core.config import SecurityConfig

@pytest.fixture
def security_config():
    """Create test security configuration."""
    return SecurityConfig(
        jwt_secret="test-jwt-secret-that-is-at-least-32-chars-long",
        jwt_algorithm="HS256",
        token_expire_minutes=15  # Short-lived tokens per design
    )

@pytest.mark.asyncio
async def test_token_lifecycle(redis_client, security_config):
    """Test complete token lifecycle including creation, validation, refresh and revocation."""
    token_manager = TokenManager(redis_client, security_config)
    
    # Create token with test data
    token_data = {
        "sub": "test_user",
        "organization_id": "test_org",
        "role": "user"
    }
    
    # Test token creation
    token = await token_manager.create_access_token(token_data)
    assert token is not None
    
    # Test token validation
    payload = await token_manager.validate_token(token)
    assert payload["sub"] == "test_user"
    assert payload["organization_id"] == "test_org"
    assert payload["role"] == "user"
    assert "exp" in payload
    
    # Test token refresh
    new_token = await token_manager.refresh_token(token)
    assert new_token != token
    new_payload = await token_manager.validate_token(new_token)
    assert new_payload["sub"] == payload["sub"]
    
    # Test token revocation
    await token_manager.revoke_token(token)
    assert await token_manager.is_token_revoked(token)
    
    # Validate revoked token fails
    with pytest.raises(HTTPException) as exc:
        await token_manager.validate_token(token)
    assert exc.value.status_code == 401
    assert "Token has been revoked" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_session_management(redis_client, security_config):
    """Test session creation, validation and termination."""
    token_manager = TokenManager(redis_client, security_config)
    
    # Create session
    session_id = "test_session"
    session_data = {
        "user_id": "test_user",
        "organization_id": "test_org",
        "role": "user"
    }
    expires_in = timedelta(hours=24)
    
    await token_manager.create_session(session_id, session_data, expires_in)
    
    # Validate session exists
    stored_session = await token_manager.get_session(session_id)
    assert stored_session is not None
    assert stored_session["user_id"] == session_data["user_id"]
    assert "access_token" in stored_session
    
    # Update session
    session_data["last_active"] = datetime.utcnow().isoformat()
    await token_manager.update_session(session_id, session_data)
    
    # End session
    await token_manager.end_session(session_id)
    ended_session = await token_manager.get_session(session_id)
    assert ended_session is None

@pytest.mark.asyncio
async def test_token_expiration(redis_client, security_config):
    """Test token expiration behavior."""
    token_manager = TokenManager(redis_client, security_config)
    
    # Create token that expires in 1 second
    token_data = {"sub": "test_user"}
    token = await token_manager.create_access_token(
        token_data,
        expires_in=timedelta(seconds=1)
    )
    
    # Token should be valid initially
    payload = await token_manager.validate_token(token)
    assert payload["sub"] == "test_user"
    
    # Wait for token to expire
    await asyncio.sleep(2)
    
    # Validation should fail with expired token
    with pytest.raises(HTTPException) as exc:
        await token_manager.validate_token(token)
    assert exc.value.status_code == 401
    assert "Token has expired" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_permission_verification(redis_client, security_config):
    """Test token permission verification."""
    token_manager = TokenManager(redis_client, security_config)
    
    # Create token with permissions
    token_data = {
        "sub": "test_user",
        "permissions": ["read:users", "write:posts"]
    }
    token = await token_manager.create_access_token(token_data)
    
    # Test permission verification
    assert token_manager.verify_permissions(token, ["read:users"])
    assert token_manager.verify_permissions(token, ["write:posts"])
    assert token_manager.verify_permissions(token, ["read:users", "write:posts"])
    assert not token_manager.verify_permissions(token, ["admin:all"])
    
    # Test with invalid token
    assert not token_manager.verify_permissions("invalid_token", ["read:users"]) 