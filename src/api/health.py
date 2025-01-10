"""Health check endpoints."""
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.dependencies import (
    DBSession,
    RedisDep,
    EventSystemDep
)

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    database: str
    event_system: str
    redis: str

router = APIRouter(prefix="/health", tags=["health"])

@router.get("", response_model=HealthResponse)
async def health_check(
    db: DBSession,
    event_system: EventSystemDep,
    redis: RedisDep
) -> HealthResponse:
    """Check health of all services.
    
    Args:
        db: Database session
        event_system: Event system instance
        redis: Redis client
        
    Returns:
        Health status of each service
        
    Raises:
        HTTPException: If any service is unhealthy
    """
    try:
        # Check database connection
        await db.execute("SELECT 1")
        
        # Check event system connection
        if not await event_system.verify_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Event system unavailable"
            )
            
        # Check Redis connection
        if not await redis.ping():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis unavailable"
            )
            
        return HealthResponse(
            status="healthy",
            database="connected",
            event_system="connected",
            redis="connected"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )