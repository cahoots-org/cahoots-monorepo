"""System metrics and monitoring endpoints."""

from datetime import datetime
from typing import Any, Dict, List

from api.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, Response, status
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from schemas.health import (
    MetricsResponse,
    MetricsSummary,
    ResourceMetrics,
    ServiceMetrics,
)
from services.health_service import HealthService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/metrics", tags=["health-metrics"])


@router.get("", response_model=APIResponse[MetricsResponse])
async def get_metrics(
    start_time: datetime = None, end_time: datetime = None, db: AsyncSession = Depends(get_db)
) -> APIResponse[MetricsResponse]:
    """Get system metrics for the specified time range."""
    try:
        service = HealthService(db)
        metrics = await service.get_metrics(start_time, end_time)

        return APIResponse(success=True, data=metrics)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="METRICS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/summary", response_model=APIResponse[MetricsSummary])
async def get_metrics_summary(db: AsyncSession = Depends(get_db)) -> APIResponse[MetricsSummary]:
    """Get summary of current system metrics."""
    try:
        service = HealthService(db)
        summary = await service.get_metrics_summary()

        return APIResponse(success=True, data=summary)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="METRICS_SUMMARY_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/resources", response_model=APIResponse[ResourceMetrics])
async def get_resource_metrics(db: AsyncSession = Depends(get_db)) -> APIResponse[ResourceMetrics]:
    """Get current resource utilization metrics."""
    try:
        service = HealthService(db)
        metrics = await service.get_resource_metrics()

        return APIResponse(success=True, data=metrics)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="RESOURCE_METRICS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/services", response_model=APIResponse[List[ServiceMetrics]])
async def get_service_metrics(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[List[ServiceMetrics]]:
    """Get metrics for individual services."""
    try:
        service = HealthService(db)
        metrics = await service.get_service_metrics()

        return APIResponse(success=True, data=metrics)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SERVICE_METRICS_ERROR",
                message=str(e),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/prometheus", response_class=Response)
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)) -> Response:
    """Get metrics in Prometheus format."""
    try:
        service = HealthService(db)
        metrics = await service.get_prometheus_metrics()

        return Response(content=metrics, media_type="text/plain")
    except Exception as e:
        return Response(content=str(e), status_code=500, media_type="text/plain")
