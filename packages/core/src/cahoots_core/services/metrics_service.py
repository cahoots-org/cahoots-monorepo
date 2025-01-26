"""Metrics collection service."""
from typing import Dict, Optional
from uuid import UUID
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.infrastructure import (
    DatabaseManager,
    RedisManager
)

from cahoots_core.utils.infrastructure.k8s.client import get_k8s_client
from cahoots_core.utils.infrastructure.redis.client import get_redis_client
from cahoots_core.utils.infrastructure.database.client import get_db_client
from cahoots_core.utils.config import Config

logger = logging.getLogger(__name__)

class MetricsService:
    """Service for collecting and managing project metrics."""

    def __init__(self, config: Config):
        """Initialize metrics service.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.k8s_client = get_k8s_client(config.k8s)
        self.redis_client = get_redis_client(config.redis)
        self.db_client = get_db_client(config.database)

    async def collect_metrics(self, project_id: UUID) -> None:
        """Collect metrics for a project."""
        try:
            # Get project resources
            namespace = f"project-{project_id}"
            redis_ns = f"project:{project_id}"
            db_schema = f"project_{project_id}"

            # Collect Kubernetes metrics
            k8s_metrics = await self._collect_k8s_metrics(namespace)

            # Collect Redis metrics
            redis_metrics = await self._collect_redis_metrics(redis_ns)

            # Collect database metrics
            db_metrics = await self._collect_db_metrics(db_schema)

            # Store metrics
            timestamp = datetime.utcnow()
            await self._store_metrics(project_id, timestamp, {
                **k8s_metrics,
                **redis_metrics,
                **db_metrics
            })

        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")
            raise

    async def get_current_usage(self, project_id: UUID) -> Dict:
        """Get current resource usage for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict: Current resource usage metrics
            
        Raises:
            ServiceError: If metrics collection fails
        """
        try:
            namespace = f"project-{project_id}"
            redis_ns = f"project:{project_id}"
            db_schema = f"project_{project_id}"

            k8s_metrics = await self._collect_k8s_metrics(namespace)
            redis_metrics = await self._collect_redis_metrics(redis_ns)
            db_metrics = await self._collect_db_metrics(db_schema)

            return {
                **k8s_metrics,
                **redis_metrics,
                **db_metrics
            }

        except Exception as e:
            logger.error(f"Failed to get current usage: {str(e)}")
            raise

    async def _collect_k8s_metrics(self, namespace: str) -> Dict:
        """Collect Kubernetes metrics.
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            Dict: Kubernetes resource metrics
        """
        try:
            metrics = await self.k8s_client.get_namespace_metrics(namespace)
            return {
                "k8s_pod_count": metrics.get("pod_count", 0),
                "k8s_total_cpu_cores": metrics.get("cpu_cores", 0),
                "k8s_total_memory_mb": metrics.get("memory_mb", 0)
            }
        except Exception as e:
            logger.error(f"Failed to collect Kubernetes metrics: {str(e)}")
            return {}

    async def _collect_redis_metrics(self, namespace: str) -> Dict:
        """Collect Redis metrics.
        
        Args:
            namespace: Redis namespace
            
        Returns:
            Dict: Redis resource metrics
        """
        try:
            metrics = await self.redis_client.get_namespace_metrics(namespace)
            return {
                "redis_memory_bytes": metrics.get("memory_bytes", 0),
                "redis_keys_count": metrics.get("keys_count", 0),
                "redis_ops_per_sec": metrics.get("ops_per_sec", 0)
            }
        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {str(e)}")
            return {}

    async def _collect_db_metrics(self, schema: str) -> Dict:
        """Collect database metrics.
        
        Args:
            schema: Database schema
            
        Returns:
            Dict: Database resource metrics
        """
        try:
            metrics = await self.db_client.get_schema_metrics(schema)
            return {
                "db_size_bytes": metrics.get("size_bytes", 0),
                "db_row_count": metrics.get("row_count", 0),
                "db_index_size_bytes": metrics.get("index_size_bytes", 0)
            }
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {str(e)}")
            return {}

    async def _store_metrics(
        self,
        project_id: UUID,
        timestamp: datetime,
        metrics: Dict
    ) -> None:
        """Store collected metrics."""
        try:
            # In a real implementation, we would store in a time-series database
            # For now, just log the metrics
            logger.info(f"Metrics for project {project_id} at {timestamp}: {metrics}")

        except Exception as e:
            logger.error(f"Failed to store metrics: {str(e)}")
            raise 