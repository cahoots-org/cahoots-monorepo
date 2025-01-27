"""Authentication and authorization utilities."""
from typing import Optional, Dict, Any
from cahoots_core.models.api_key import APIKey
from cahoots_core.models.user import User
from fastapi import Depends, HTTPException, status, APIRouter, Form
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from cahoots_core.utils.config import get_settings
from cahoots_service.api.dependencies import get_db
from cahoots_service.utils.security import hash_api_key

# API key header scheme
api_key_scheme = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str, db: AsyncSession) -> str:
    """Verify API key and return organization ID.
    
    Args:
        api_key: API key to verify
        db: Database session
        
    Returns:
        str: Organization ID associated with API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
        
    # Look up API key
    stmt = select(APIKey).where(APIKey.hashed_key == hash_api_key(api_key))
    result = await db.execute(stmt)
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
        
    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive"
        )
        
    return api_key_obj.organization_id

async def get_current_user(
    api_key: str = Depends(api_key_scheme),
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

@router.post("/verify")
async def verify_token(
    api_key: str = Depends(api_key_scheme),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Verify API key and return user info.
    
    Args:
        api_key: API key from request header
        db: Database session
        
    Returns:
        Dict containing user and organization info
        
    Raises:
        HTTPException: If API key is invalid
    """
    user = await get_current_user(api_key, db)
    organization_id = await verify_api_key(api_key, db)
    
    return {
        "user_id": str(user.id),
        "organization_id": str(organization_id),
        "username": user.username,
        "email": user.email
    } 