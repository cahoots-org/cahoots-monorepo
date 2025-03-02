"""Health check and monitoring service implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.dependencies import (
    check_database,
    check_external_apis,
    check_message_queue,
    check_redis,
    check_storage,
)
from redis.asyncio import Redis
from schemas.health import (
    DependencyCheckResponse,
    DependencyDetails,
    DependencyMetrics,
    DependencyStatus,
    DependencyType,
    HealthCheckResponse,
    HealthStatus,
    MetricValue,
)
from sqlalchemy.ext.asyncio import AsyncSession
from utils.config import get_settings

from cahoots_core.utils.infrastructure.database.client import get_db_client
from cahoots_core.utils.infrastructure.k8s.client import KubernetesClient
from cahoots_core.utils.infrastructure.redis.client import RedisClient
from cahoots_core.utils.infrastructure.stripe.client import get_stripe_client

settings = get_settings()


class HealthService:
    """Service for system health monitoring and dependency checks."""

    def __init__(self, db: AsyncSession):
        """Initialize health service."""
        self.db = db
        self._start_time = datetime.utcnow()
        self._dependencies = {
            "database": {
                "type": DependencyType.DATABASE,
                "check": check_database,
                "is_critical": True,
            },
            "redis": {"type": DependencyType.CACHE, "check": check_redis, "is_critical": True},
            "message_queue": {
                "type": DependencyType.MESSAGE_QUEUE,
                "check": check_message_queue,
                "is_critical": True,
            },
            "storage": {
                "type": DependencyType.STORAGE,
                "check": check_storage,
                "is_critical": False,
            },
            "external_apis": {
                "type": DependencyType.EXTERNAL_API,
                "check": check_external_apis,
                "is_critical": False,
            },
        }

    async def get_dependencies_status(self) -> List[DependencyStatus]:
        """Get status of all system dependencies."""
        statuses = []
        for name, config in self._dependencies.items():
            status = await self._check_dependency(name)
            statuses.append(status)
        return statuses

    async def check_dependencies(self) -> DependencyCheckResponse:
        """Run health checks on all dependencies."""
        dependencies = await self.get_dependencies_status()

        healthy_count = sum(1 for d in dependencies if d.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for d in dependencies if d.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for d in dependencies if d.status == HealthStatus.UNHEALTHY)

        # Determine overall status based on critical dependencies
        overall_status = HealthStatus.HEALTHY
        for dep in dependencies:
            if dep.is_critical:
                if dep.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                elif dep.status == HealthStatus.DEGRADED:
                    overall_status = HealthStatus.DEGRADED

        return DependencyCheckResponse(
            overall_status=overall_status,
            dependencies=dependencies,
            timestamp=datetime.utcnow(),
            total_dependencies=len(dependencies),
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            unhealthy_count=unhealthy_count,
        )

    async def get_dependency_details(self, dependency_name: str) -> DependencyDetails:
        """Get detailed status and metrics for a specific dependency."""
        if dependency_name not in self._dependencies:
            raise ValueError(f"Unknown dependency: {dependency_name}")

        status = await self._check_dependency(dependency_name)
        metrics = await self._get_dependency_metrics(dependency_name)
        config = await self._get_dependency_config(dependency_name)
        version = await self._get_dependency_version(dependency_name)
        uptime = await self._get_dependency_uptime(dependency_name)

        return DependencyDetails(
            status=status, metrics=metrics, config=config, version=version, uptime=uptime
        )

    async def verify_dependency(self, dependency_name: str) -> bool:
        """Verify connectivity and functionality of a specific dependency."""
        if dependency_name not in self._dependencies:
            raise ValueError(f"Unknown dependency: {dependency_name}")

        status = await self._check_dependency(dependency_name)
        return status.status == HealthStatus.HEALTHY

    async def get_critical_dependencies(self) -> List[DependencyStatus]:
        """Get status of critical system dependencies."""
        all_statuses = await self.get_dependencies_status()
        return [status for status in all_statuses if status.is_critical]

    async def _check_dependency(self, name: str) -> DependencyStatus:
        """Check health status of a specific dependency."""
        config = self._dependencies[name]
        start_time = datetime.utcnow()

        try:
            status = await config["check"](self.db)
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            return DependencyStatus(
                name=name,
                type=config["type"],
                status=status,
                last_check=datetime.utcnow(),
                latency_ms=latency,
                is_critical=config["is_critical"],
                message=None,
            )
        except Exception as e:
            return DependencyStatus(
                name=name,
                type=config["type"],
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                latency_ms=0.0,
                is_critical=config["is_critical"],
                message=str(e),
            )

    async def _get_dependency_metrics(self, name: str) -> DependencyMetrics:
        """Get metrics for a specific dependency."""
        # Implementation would vary based on monitoring system integration
        return DependencyMetrics(
            latency=MetricValue(value=0.0, unit="ms", timestamp=datetime.utcnow()),
            error_rate=MetricValue(value=0.0, unit="errors/second", timestamp=datetime.utcnow()),
            throughput=MetricValue(value=0.0, unit="requests/second", timestamp=datetime.utcnow()),
        )

    async def _get_dependency_config(self, name: str) -> Dict[str, Any]:
        """Get configuration for a specific dependency."""
        # Implementation would return sanitized configuration
        return {}

    async def _get_dependency_version(self, name: str) -> Optional[str]:
        """Get version information for a specific dependency."""
        # Implementation would vary based on dependency
        return None

    async def _get_dependency_uptime(self, name: str) -> Optional[float]:
        """Get uptime for a specific dependency."""
        # Implementation would vary based on dependency
        return None
