"""Status page endpoints."""
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import REGISTRY, Gauge, Counter, Histogram
from redis.asyncio import Redis

from cahoots_core.exceptions import ServiceError
from cahoots_service.api.dependencies import BaseDeps
from cahoots_service.schemas.status import (
    SystemStatusResponse,
    ServiceHealth,
    MetricsSummary,
    ProjectMetrics
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["status"])

# Define Prometheus metrics
ERROR_RATE = Counter('api_error_rate', 'API error rate')
LATENCY = Histogram('api_latency_seconds', 'API latency in seconds')
REQUEST_RATE = Counter('api_requests_total', 'Total API requests')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')

# Project metrics
ACTIVE_PROJECTS = Gauge('active_projects_total', 'Number of active projects')
COMPLETED_TASKS = Counter('completed_tasks_total', 'Number of completed tasks')
TASK_SUCCESS_RATE = Gauge('task_success_rate', 'Task success rate')

@router.get("", response_model=SystemStatusResponse)
async def get_system_status(deps: BaseDeps = Depends()) -> SystemStatusResponse:
    """Get system status and key metrics.
    
    Args:
        deps: Base dependencies including db, redis, and event system
        
    Returns:
        System status including service health and metrics
        
    Raises:
        HTTPException: If status check fails
    """
    try:
        # Get service health
        services = {
            "api": await _check_api_health(),
            "database": await _check_db_health(deps.db),
            "redis": await _check_redis_health(deps.redis),
            "event_system": await _check_event_system_health(deps.event_system),
            "agents": await _get_agent_health(deps.redis)
        }

        # Get key metrics
        metrics = await _get_key_metrics()
        
        # Get project metrics
        project_metrics = await _get_project_metrics()

        return SystemStatusResponse(
            services=services,
            metrics=metrics,
            project_metrics=project_metrics
        )
    except Exception as e:
        logger.error("Error getting system status: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )

async def _check_api_health() -> ServiceHealth:
    """Check API health."""
    return ServiceHealth(
        status="healthy",
        message="API is responding"
    )

async def _check_db_health(db: AsyncSession) -> ServiceHealth:
    """Check database health."""
    try:
        await db.execute("SELECT 1")
        return ServiceHealth(
            status="healthy",
            message="Database is connected"
        )
    except Exception as e:
        logger.error("Database health check failed: %s", str(e), exc_info=True)
        return ServiceHealth(
            status="unhealthy",
            message=f"Database error: {str(e)}"
        )

async def _check_redis_health(redis: Redis) -> ServiceHealth:
    """Check Redis health."""
    try:
        await redis.ping()
        info = await redis.info()
        used_memory = info['used_memory_human']
        return ServiceHealth(
            status="healthy",
            message=f"Redis is connected (Memory: {used_memory})"
        )
    except Exception as e:
        logger.error("Redis health check failed: %s", str(e), exc_info=True)
        return ServiceHealth(
            status="unhealthy",
            message=f"Redis error: {str(e)}"
        )

async def _check_event_system_health(event_system) -> ServiceHealth:
    """Check event system health."""
    try:
        await event_system.verify_connection()
        return ServiceHealth(
            status="healthy",
            message="Event system is connected"
        )
    except Exception as e:
        logger.error("Event system health check failed: %s", str(e), exc_info=True)
        return ServiceHealth(
            status="unhealthy",
            message=f"Event system error: {str(e)}"
        )

async def _get_agent_health(redis: Redis) -> Dict[str, ServiceHealth]:
    """Get health status of all agents."""
    agents = {}
    agent_types = ["developer", "qa", "ux"]
    
    for agent_type in agent_types:
        try:
            last_heartbeat = await redis.get(f"agent:{agent_type}:heartbeat")
            if last_heartbeat:
                agents[agent_type] = ServiceHealth(
                    status="healthy",
                    message="Agent is running"
                )
            else:
                agents[agent_type] = ServiceHealth(
                    status="unhealthy",
                    message="No recent heartbeat"
                )
        except Exception as e:
            logger.error("Agent health check failed for %s: %s", agent_type, str(e), exc_info=True)
            agents[agent_type] = ServiceHealth(
                status="unknown",
                message=f"Error checking agent: {str(e)}"
            )
    
    return agents

async def _get_key_metrics() -> MetricsSummary:
    """Get key system metrics."""
    try:
        return MetricsSummary(
            error_rate=REGISTRY.get_sample_value('api_error_rate') or 0.0,
            latency_p95=REGISTRY.get_sample_value('api_latency_seconds_sum') or 0.0,
            requests_per_minute=REGISTRY.get_sample_value('api_requests_total') or 0.0,
            memory_usage=REGISTRY.get_sample_value('memory_usage_bytes') or 0.0,
            cpu_usage=REGISTRY.get_sample_value('cpu_usage_percent') or 0.0
        )
    except Exception as e:
        logger.error("Error getting metrics: %s", str(e), exc_info=True)
        return MetricsSummary(
            error_rate=0.0,
            latency_p95=0.0,
            requests_per_minute=0.0,
            memory_usage=0.0,
            cpu_usage=0.0
        )

async def _get_project_metrics() -> Optional[ProjectMetrics]:
    """Get project-related metrics."""
    try:
        active = REGISTRY.get_sample_value('active_projects_total') or 0.0
        completed = REGISTRY.get_sample_value('completed_tasks_total') or 0.0
        success = REGISTRY.get_sample_value('task_success_rate') or 0.0

        return ProjectMetrics(
            active_projects=int(active),
            completed_tasks=int(completed),
            success_rate=success
        )
    except Exception as e:
        logger.error("Error getting project metrics: %s", str(e), exc_info=True)
        return None 