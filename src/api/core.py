"""Core API functionality."""
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from src.models.user import User
from src.models.session import Session
from src.models.api_key import APIKey
from src.utils.security import hash_api_key, create_session_token
from .dependencies import (
    get_db,
    get_stripe_client,
    DBSession,
    EventSystemDep,
    StripeClientDep,
)

async def get_current_user(
    db: DBSession = Depends(get_db),
    event_system: EventSystemDep = Depends(),
    stripe: Optional[StripeClientDep] = Depends(get_stripe_client)
) -> Tuple[User, Session]:
    """Get current authenticated user and their session.
    
    Args:
        db: Database session
        event_system: Event system instance
        stripe: Optional Stripe client
        
    Returns:
        Tuple[User, Session]: Current user and their session
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get API key from header
        api_key = event_system.request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key"
            )
            
        # Look up API key
        stmt = select(APIKey).where(
            APIKey.hashed_key == hash_api_key(api_key),
            APIKey.is_active == True
        )
        result = await db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key or db_key.is_expired():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key"
            )
            
        # Get user
        stmt = select(User).where(User.id == db_key.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Create or get existing session
        session = await get_or_create_session(db, user.id, api_key)
        
        return user, session
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_or_create_session(
    db: AsyncSession,
    user_id: str,
    api_key: str
) -> Session:
    """Get existing session or create new one.
    
    Args:
        db: Database session
        user_id: User ID
        api_key: API key used for authentication
        
    Returns:
        Session: User session
    """
    # Look for existing valid session
    stmt = select(Session).where(
        Session.user_id == user_id,
        Session.expires_at > datetime.utcnow()
    ).order_by(Session.created_at.desc())
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if session:
        return session
        
    # Create new session
    session = Session(
        user_id=user_id,
        token=create_session_token(),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(session)
    await db.commit()
    
    return session 