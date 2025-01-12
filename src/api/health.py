"""Health check endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import time

from src.core.dependencies import BaseDeps

router = APIRouter(tags=["health"])

class RedisHealth(BaseModel):
    """Redis health details."""
    status: str
    latency_ms: float
    details: dict = {}

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    database: str
    event_system: str
    redis: str
    services: dict = {"redis": RedisHealth(status="healthy", latency_ms=0.0, details={})}

@router.get("")
async def health_check(
    deps: BaseDeps = Depends(BaseDeps)
) -> HealthResponse:
    """Check health of all services."""
    # Initialize status tracking
    statuses = {
        "database": "connected",
        "event_system": "connected",
        "redis": "connected"
    }
    
    # Check database
    try:
        await deps.db.execute("SELECT 1")
    except Exception:
        statuses["database"] = "unavailable"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )
        
    # Check event system
    try:
        await deps.event_system.verify_connection()
    except Exception:
        statuses["event_system"] = "unavailable"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event system unavailable"
        )
        
    # Check Redis with latency
    try:
        start_time = time.time()
        await deps.redis.ping()
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        redis_health = RedisHealth(
            status="healthy",
            latency_ms=latency,
            details={}
        )
    except Exception:
        statuses["redis"] = "unavailable"
        redis_health = RedisHealth(
            status="unavailable",
            latency_ms=0.0,
            details={"error": "Redis connection failed"}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable"
        )
        
    return HealthResponse(
        status="healthy",
        database=statuses["database"],
        event_system=statuses["event_system"],
        redis=statuses["redis"],
        services={"redis": redis_health}
    )