"""Health check endpoints."""
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from cahoots_service.api.dependencies import ServiceDeps

router = APIRouter(prefix="/health", tags=["health"])

class ServiceHealth(BaseModel):
    """Health status for an individual service."""
    status: str
    latency_ms: float
    details: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "healthy"
    database: str = "unknown"
    redis: str = "unknown"
    event_system: str = "unknown"
    services: Dict[str, ServiceHealth] = {}

async def check_service(name: str, check_func: Any) -> ServiceHealth:
    """Check health of a service and measure latency."""
    start_time = time.time()
    try:
        await check_func()
        latency = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="healthy",
            latency_ms=latency,
            details={}
        )
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="unhealthy",
            latency_ms=latency,
            details={"error": str(e)}
        )

@router.get("/")
async def health_check(deps: ServiceDeps = Depends(ServiceDeps)) -> HealthResponse:
    """Health check endpoint that verifies all critical services."""
    response = HealthResponse()
    
    # Check database
    db_health = await check_service(
        "database",
        lambda: deps.db.execute("SELECT 1")
    )
    response.services["database"] = db_health
    response.database = "connected" if db_health.status == "healthy" else "error"
    
    # Check Redis
    redis_health = await check_service(
        "redis",
        deps.redis.ping
    )
    response.services["redis"] = redis_health
    response.redis = "connected" if redis_health.status == "healthy" else "error"
    
    # Check event system
    event_health = await check_service(
        "event_system",
        deps.event_bus.verify_connection
    )
    response.services["event_system"] = event_health
    response.event_system = "connected" if event_health.status == "healthy" else "error"

    # Set overall status
    if any(s.status == "unhealthy" for s in response.services.values()):
        response.status = "unhealthy"
        failing_service = next(name for name, s in response.services.items() if s.status == "unhealthy")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{failing_service} health check failed: {response.services[failing_service].details.get('error', 'Unknown error')}"
        )

    return response