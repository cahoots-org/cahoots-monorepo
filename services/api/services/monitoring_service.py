"""Project monitoring service."""

import asyncio
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from services.project_service import ProjectService

from cahoots_core.utils.infrastructure.redis.client import get_redis_client


class MonitoringService:
    """Service for monitoring project status and metrics."""

    def __init__(self, project_service: ProjectService):
        """Initialize monitoring service.

        Args:
            project_service: Project service instance
        """
        self.project_service = project_service
        self.redis = get_redis_client()

    async def monitor_project_creation(
        self, project_id: UUID, organization_id: UUID, timeout_seconds: int = 300
    ) -> None:
        """Monitor project creation progress and update status.

        Args:
            project_id: Project ID to monitor
            organization_id: Organization ID
            timeout_seconds: Maximum time to monitor in seconds
        """
        status_key = f"project:{project_id}:status"
        ws_channel = f"org:{organization_id}:projects"

        try:
            # Initialize status
            await self.redis.hset(
                status_key,
                mapping={
                    "status": "initializing",
                    "progress": 0,
                    "started_at": datetime.utcnow().isoformat(),
                    "last_update": datetime.utcnow().isoformat(),
                },
            )

            # Monitor for specified duration
            start_time = datetime.utcnow()
            while (datetime.utcnow() - start_time).seconds < timeout_seconds:
                # Get current status
                project = await self.project_service.get_project(project_id)
                if not project:
                    raise Exception("Project not found")

                # Update status
                status_update = {
                    "status": project.status,
                    "progress": project.progress,
                    "last_update": datetime.utcnow().isoformat(),
                }
                await self.redis.hset(status_key, mapping=status_update)

                # Publish WebSocket update
                await self.redis.publish(
                    ws_channel,
                    {
                        "type": "project_update",
                        "project_id": str(project_id),
                        "data": status_update,
                    },
                )

                # Check if complete
                if project.status in ["ready", "failed"]:
                    break

                await asyncio.sleep(5)

            # Handle timeout
            if project.status not in ["ready", "failed"]:
                await self.project_service.update_project(
                    project_id, {"status": "failed", "error": "Project creation timed out"}
                )

        except Exception as e:
            # Handle monitoring failure
            try:
                await self.redis.hset(
                    status_key,
                    mapping={
                        "status": "failed",
                        "error": str(e),
                        "last_update": datetime.utcnow().isoformat(),
                    },
                )
                await self.project_service.update_project(
                    project_id, {"status": "failed", "error": str(e)}
                )
            except Exception:
                pass  # Prevent monitoring errors from cascading
