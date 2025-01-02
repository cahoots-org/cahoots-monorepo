from fastapi import APIRouter, status, Response, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Annotated
import psutil
import time
from datetime import datetime
from ..utils.event_system import EventSystem
from ..utils.logger import Logger
from ..utils.config import config
from ..utils.metrics import get_metrics
from .core import get_event_system

router = APIRouter()
logger = Logger("Health")

class ServiceHealth(BaseModel):
    """Service health details."""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    latency_ms: float = Field(..., description="Service latency in milliseconds")
    last_check: datetime = Field(..., description="Last health check timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")

class SystemMetrics(BaseModel):
    """System resource metrics."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_percent: float = Field(..., description="Disk usage percentage")
    open_file_descriptors: int = Field(..., description="Number of open file descriptors")

class HealthResponse(BaseModel):
    """Complete health check response."""
    status: str = Field(..., description="Overall system health status")
    environment: str = Field(..., description="Current environment")
    version: str = Field(..., description="Application version")
    uptime_seconds: int = Field(..., description="Application uptime in seconds")
    system_metrics: SystemMetrics = Field(..., description="System resource metrics")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service health status")
    redis_connected: bool = Field(..., description="Redis connection status")
    metrics: Dict[str, Any] = Field(..., description="Application metrics")

start_time = time.time()

async def check_service_health(service_name: str, url: str, event_system: EventSystem) -> ServiceHealth:
    """Check health of an individual service."""
    try:
        start = time.time()
        if service_name == "redis":
            redis = await event_system.get_redis()
            await redis.ping()
        # Add other service health checks here
        
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            status="healthy",
            latency_ms=latency,
            last_check=datetime.utcnow(),
            details={"url": url}
        )
    except Exception as e:
        logger.error(f"Health check failed for {service_name}", error=str(e))
        return ServiceHealth(
            status="unhealthy",
            latency_ms=0,
            last_check=datetime.utcnow(),
            details={"error": str(e)}
        )

def get_system_metrics() -> SystemMetrics:
    """Get system resource metrics."""
    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage('/').percent,
        open_file_descriptors=psutil.Process().num_fds()
    )

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Get comprehensive health status of the system and its services",
    responses={
        503: {"description": "Service Unavailable"}
    }
)
async def get_health_check(
    response: Response,
    event_system: Annotated[EventSystem, Depends(get_event_system)]
) -> Dict:
    """Health check endpoint.
    
    Returns:
        Dict: Detailed health status information
    """
    services = {}
    is_healthy = True
    redis_connected = False

    # Check Redis health
    try:
        start = time.time()
        redis_connected = await event_system.verify_connection()
        latency = round((time.time() - start) * 1000, 2)
        
        services["redis"] = ServiceHealth(
            status="healthy" if redis_connected else "unhealthy",
            latency_ms=latency,
            last_check=datetime.utcnow(),
            details={}
        )
        
        if not redis_connected:
            is_healthy = False
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        services["redis"] = ServiceHealth(
            status="unhealthy",
            latency_ms=0,
            last_check=datetime.utcnow(),
            details={"error": str(e)}
        )
        is_healthy = False
        redis_connected = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Get system metrics
    system_metrics = get_system_metrics()

    # Get application metrics
    metrics = get_metrics()

    # Build response
    health_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "environment": config.env,
        "version": config.api.version,
        "uptime_seconds": int(time.time() - start_time),
        "system_metrics": system_metrics,
        "services": services,
        "redis_connected": redis_connected,
        "metrics": metrics
    }

    return health_data 