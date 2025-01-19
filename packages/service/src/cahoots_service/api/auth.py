"""Authentication and authorization utilities."""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, APIRouter, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.api.dependencies import get_db
from src.models.user import User
from src.models.api_key import APIKey
from src.utils.security import hash_api_key, SecurityManager
from src.core.dependencies import get_security_manager
from src.core.config import SecurityConfig
from src.api.auth.verify import api_key_header, verify_api_key

async def get_current_user(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from API key.
    
    Args:
        api_key: API key from request header
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If API key is invalid or user not found
    """
    organization_id = await verify_api_key(api_key, db)
    
    # Look up user associated with API key
    stmt = select(User).join(
        APIKey, User.id == APIKey.user_id
    ).where(
        APIKey.hashed_key == hash_api_key(api_key)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return user 

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class LoginForm:
    """Form for handling login requests."""
    def __init__(
        self,
        username: str = Form(),
        password: str = Form(),
        grant_type: str = Form(default="password"),
        scope: str = Form(default=""),
        client_id: str | None = Form(default=None),
        client_secret: str | None = Form(default=None)
    ):
        self.username = username
        self.password = password
        self.grant_type = grant_type
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret

@router.post("/token")
async def login(
    form_data: LoginForm = Depends(),
    security_config: SecurityConfig = Depends(),
    security_manager: SecurityManager = Depends()
) -> Dict[str, Any]:
    """Login endpoint that returns an access token.
    
    Args:
        form_data: The login form data
        security_config: Security configuration
        security_manager: Security manager instance
        
    Returns:
        Dict containing the access token
        
    Raises:
        HTTPException: If authentication fails
    """
    access_token = await security_manager.authenticate_user(
        form_data.username,
        form_data.password,
        form_data.scopes
    )
    return {"access_token": access_token, "token_type": "bearer"} 