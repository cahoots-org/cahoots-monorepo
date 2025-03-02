import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import psutil
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class SystemStatus(BaseModel):
    """System status model"""

    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, float]
    uptime: float
    process_count: int
    last_updated: datetime


class ServiceStatus(BaseModel):
    """Service status model"""

    name: str
    status: str
    latency: float
    last_check: datetime
    error: Optional[str] = None


class ServiceHealthCheck:
    """Service health check implementation"""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store
        self.start_time = time.time()

    def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        try:
            return SystemStatus(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_usage={
                    path.mountpoint: psutil.disk_usage(path.mountpoint).percent
                    for path in psutil.disk_partitions()
                },
                uptime=time.time() - self.start_time,
                process_count=len(psutil.pids()),
                last_updated=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise

    async def check_service_health(self) -> List[ServiceStatus]:
        """Check health of all services"""
        services = []

        # Check event store
        event_store_status = await self._check_event_store()
        services.append(event_store_status)

        # Check view store
        view_store_status = await self._check_view_store()
        services.append(view_store_status)

        return services

    async def _check_event_store(self) -> ServiceStatus:
        """Check event store health"""
        start_time = time.time()
        try:
            # Try to get all events (with a limit)
            events = self.event_store.get_all_events()[:10]
            latency = time.time() - start_time

            return ServiceStatus(
                name="event_store", status="healthy", latency=latency, last_check=datetime.utcnow()
            )
        except Exception as e:
            return ServiceStatus(
                name="event_store",
                status="unhealthy",
                latency=time.time() - start_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )

    async def _check_view_store(self) -> ServiceStatus:
        """Check view store health"""
        start_time = time.time()
        try:
            # Try to get a view (any view will do)
            views = self.view_store.get_all_views()
            latency = time.time() - start_time

            return ServiceStatus(
                name="view_store", status="healthy", latency=latency, last_check=datetime.utcnow()
            )
        except Exception as e:
            return ServiceStatus(
                name="view_store",
                status="unhealthy",
                latency=time.time() - start_time,
                last_check=datetime.utcnow(),
                error=str(e),
            )


# Router endpoints


@router.get("/system")
async def get_system_status(request: Request):
    """Get system status"""
    health_check = ServiceHealthCheck(request.state.event_store, request.state.view_store)
    return health_check.get_system_status()


@router.get("/services")
async def get_service_status(request: Request):
    """Get service status"""
    health_check = ServiceHealthCheck(request.state.event_store, request.state.view_store)
    services = await health_check.check_service_health()
    return {"services": services}


@router.get("/health")
async def health_check(request: Request):
    """Comprehensive health check"""
    health_check = ServiceHealthCheck(request.state.event_store, request.state.view_store)

    try:
        # Get both system and service status
        system_status = health_check.get_system_status()
        service_status = await health_check.check_service_health()

        # Check if any service is unhealthy
        all_healthy = all(service.status == "healthy" for service in service_status)

        return {
            "status": "healthy" if all_healthy else "degraded",
            "system": system_status,
            "services": service_status,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
