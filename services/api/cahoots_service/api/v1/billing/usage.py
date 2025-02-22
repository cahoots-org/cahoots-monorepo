"""Usage tracking and reporting endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from cahoots_service.api.dependencies import get_db, get_current_user
from cahoots_service.schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from cahoots_service.schemas.billing import (
    UsageResponse,
    UsageDetailResponse,
    UsageSummaryResponse
)
from cahoots_core.services.billing import BillingService
from cahoots_core.models.user import User

router = APIRouter(prefix="/usage", tags=["billing-usage"])

@router.get("", response_model=APIResponse[UsageSummaryResponse])
async def get_usage_summary(
    start_date: datetime = None,
    end_date: datetime = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[UsageSummaryResponse]:
    """Get usage summary for the current billing period."""
    try:
        service = BillingService(db)
        summary = await service.get_usage_summary(
            current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        return APIResponse(
            success=True,
            data=summary
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="USAGE_SUMMARY_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/details", response_model=APIResponse[List[UsageDetailResponse]])
async def get_usage_details(
    start_date: datetime = None,
    end_date: datetime = None,
    service_type: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[UsageDetailResponse]]:
    """Get detailed usage breakdown by service type."""
    try:
        service = BillingService(db)
        details = await service.get_usage_details(
            current_user.id,
            start_date=start_date,
            end_date=end_date,
            service_type=service_type
        )
        
        return APIResponse(
            success=True,
            data=details
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="USAGE_DETAILS_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/current", response_model=APIResponse[UsageResponse])
async def get_current_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[UsageResponse]:
    """Get current usage metrics for the active billing period."""
    try:
        service = BillingService(db)
        usage = await service.get_current_usage(current_user.id)
        
        return APIResponse(
            success=True,
            data=usage
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="CURRENT_USAGE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/forecast", response_model=APIResponse[Dict[str, Any]])
async def get_usage_forecast(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get usage forecast based on current trends."""
    try:
        service = BillingService(db)
        forecast = await service.get_usage_forecast(current_user.id, days)
        
        return APIResponse(
            success=True,
            data=forecast
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="USAGE_FORECAST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/limits", response_model=APIResponse[Dict[str, Any]])
async def get_usage_limits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get current usage limits and thresholds."""
    try:
        service = BillingService(db)
        limits = await service.get_usage_limits(current_user.id)
        
        return APIResponse(
            success=True,
            data=limits
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="USAGE_LIMITS_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 