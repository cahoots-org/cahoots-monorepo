"""Project monitoring utilities."""

from typing import Any, Dict

from cahoots_core.utils.infrastructure.redis.client import get_redis_client


async def monitor_project_creation(project_id: str, metrics: Dict[str, Any]) -> None:
    """Monitor project creation metrics.

    Args:
        project_id: Project ID to monitor
        metrics: Metrics to record
    """
    redis = get_redis_client()
    await redis.hset(f"project:{project_id}:metrics", mapping=metrics)


async def get_project_metrics(project_id: str) -> Dict[str, Any]:
    """Get project metrics.

    Args:
        project_id: Project ID

    Returns:
        Dict of metrics
    """
    redis = get_redis_client()
    return await redis.hgetall(f"project:{project_id}:metrics")
