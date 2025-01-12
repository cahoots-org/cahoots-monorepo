"""Authentication and authorization utilities."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.api.dependencies import get_db
from src.models.user import User
from src.models.api_key import APIKey
from src.utils.security import hash_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Verify API key.
    
    Args:
        api_key: API key from request header
        db: Database session
        
    Returns:
        str: Organization ID associated with the API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key required"
        )
    
    # Hash the API key for comparison
    hashed_key = hash_api_key(api_key)
    
    # Look up API key in database
    stmt = select(APIKey).where(
        APIKey.hashed_key == hashed_key,
        APIKey.is_active == True
    )
    result = await db.execute(stmt)
    db_key = result.scalar_one_or_none()
    
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
        
    # Check if key is expired
    if db_key.is_expired():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired"
        )
        
    return db_key.organization_id

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