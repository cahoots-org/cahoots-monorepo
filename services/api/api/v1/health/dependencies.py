"""System dependencies health check endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from api.dependencies import get_db
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.health import (
    DependencyStatus,
    DependencyCheckResponse,
    DependencyDetails
)
from services.health_service import HealthService

router = APIRouter(prefix="/dependencies", tags=["health-dependencies"])

@router.get("", response_model=APIResponse[List[DependencyStatus]])
async def get_dependencies_status(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[DependencyStatus]]:
    """Get status of all system dependencies."""
    try:
        service = HealthService(db)
        status = await service.get_dependencies_status()
        
        return APIResponse(
            success=True,
            data=status
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="DEPENDENCIES_STATUS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/check", response_model=APIResponse[DependencyCheckResponse])
async def check_dependencies(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[DependencyCheckResponse]:
    """Run health checks on all dependencies."""
    try:
        service = HealthService(db)
        result = await service.check_dependencies()
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="DEPENDENCIES_CHECK_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/{dependency_name}", response_model=APIResponse[DependencyDetails])
async def get_dependency_details(
    dependency_name: str,
    db: AsyncSession = Depends(get_db)
) -> APIResponse[DependencyDetails]:
    """Get detailed status and metrics for a specific dependency."""
    try:
        service = HealthService(db)
        details = await service.get_dependency_details(dependency_name)
        
        return APIResponse(
            success=True,
            data=details
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="DEPENDENCY_DETAILS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("/{dependency_name}/verify", response_model=APIResponse[bool])
async def verify_dependency(
    dependency_name: str,
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Verify connectivity and functionality of a specific dependency."""
    try:
        service = HealthService(db)
        is_verified = await service.verify_dependency(dependency_name)
        
        return APIResponse(
            success=True,
            data=is_verified
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="DEPENDENCY_VERIFY_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/critical", response_model=APIResponse[List[DependencyStatus]])
async def get_critical_dependencies(
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[DependencyStatus]]:
    """Get status of critical system dependencies."""
    try:
        service = HealthService(db)
        status = await service.get_critical_dependencies()
        
        return APIResponse(
            success=True,
            data=status
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="CRITICAL_DEPENDENCIES_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            )
        ) 