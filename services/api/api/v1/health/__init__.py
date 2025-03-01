"""Health check and monitoring endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from api.dependencies import get_db, get_security_manager
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.health import (
    HealthStatus,
    ServiceStatus,
    MetricsResponse,
    DependencyStatus
)
from services.health_service import HealthService

from .metrics import router as metrics_router
from .dependencies import router as dependencies_router

router = APIRouter(prefix="/health", tags=["health"])

# Include sub-routers
router.include_router(metrics_router)
router.include_router(dependencies_router)

@router.get("", response_model=APIResponse[HealthStatus])
async def get_health_status(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[HealthStatus]:
    """Get overall system health status."""
    try:
        service = HealthService(db)
        status = await service.get_health_status()
        
        return APIResponse(
            success=True,
            data=status
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="HEALTH_CHECK_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/services", response_model=APIResponse[List[ServiceStatus]])
async def get_service_status(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[ServiceStatus]]:
    """Get status of all system services."""
    try:
        service = HealthService(db)
        statuses = await service.get_service_status()
        
        return APIResponse(
            success=True,
            data=statuses
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SERVICE_STATUS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/readiness", response_model=APIResponse[bool])
async def readiness_check(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Check if the system is ready to handle requests."""
    try:
        service = HealthService(db)
        is_ready = await service.check_readiness()
        
        return APIResponse(
            success=True,
            data=is_ready
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="READINESS_CHECK_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/liveness", response_model=APIResponse[bool])
async def liveness_check() -> APIResponse[bool]:
    """Check if the system is alive."""
    return APIResponse(
        success=True,
        data=True
    ) 