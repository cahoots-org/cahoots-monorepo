"""Health check endpoints."""

from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_redis_client, get_task_storage
from app.storage import RedisClient, TaskStorage


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cahoots-monolith",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check(
    redis: RedisClient = Depends(get_redis_client),
    storage: TaskStorage = Depends(get_task_storage)
) -> Dict[str, Any]:
    """Readiness check with dependency verification."""
    checks = {
        "redis": False,
        "storage": False
    }

    # Check Redis connection
    try:
        await redis.redis.ping()
        checks["redis"] = True
    except Exception as e:
        print(f"Redis health check failed: {e}")

    # Check storage (which uses Redis)
    try:
        # Try to count tasks
        await storage.count_tasks_by_status()
        checks["storage"] = True
    except Exception as e:
        print(f"Storage health check failed: {e}")

    # Overall status
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_healthy,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/metrics")
async def metrics(storage: TaskStorage = Depends(get_task_storage)) -> Dict[str, Any]:
    """Get application metrics."""
    try:
        task_counts = await storage.count_tasks_by_status()
        total_tasks = sum(task_counts.values())

        return {
            "tasks": {
                "total": total_tasks,
                "by_status": {
                    status.value: count
                    for status, count in task_counts.items()
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }