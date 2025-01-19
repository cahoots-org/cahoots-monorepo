"""Project monitoring utilities."""
import asyncio
from datetime import datetime
from typing import Dict
from uuid import UUID

from src.core.config import Settings
from src.services.project_service import ProjectService
from src.utils.infrastructure import RedisClient, get_redis_client

async def monitor_project_creation(
    project_id: UUID,
    organization_id: UUID,
    settings: Settings,
    project_service: ProjectService,
    redis_client: RedisClient = None
):
    """Monitor project creation progress and update status.
    
    This runs as a background task and:
    1. Monitors resource creation progress
    2. Updates project status in Redis
    3. Publishes status updates via WebSocket
    4. Handles timeouts and failures
    """
    redis = redis_client or get_redis_client()
    status_key = f"project:{project_id}:status"
    ws_channel = f"org:{organization_id}:projects"
    
    try:
        # Initialize status
        await redis.set(
            status_key,
            {
                "status": "initializing",
                "progress": 0,
                "started_at": datetime.utcnow().isoformat(),
                "last_update": datetime.utcnow().isoformat()
            }
        )
        
        # Monitor for up to 5 minutes
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).seconds < 300:
            # Get current status
            project = await project_service.get_project(project_id)
            if not project:
                raise Exception("Project not found")
                
            # Update status
            status_update = {
                "status": project.status,
                "progress": project.progress,
                "last_update": datetime.utcnow().isoformat()
            }
            await redis.set(status_key, status_update)
            
            # Publish WebSocket update
            await redis.publish(
                ws_channel,
                {
                    "type": "project_update",
                    "project_id": str(project_id),
                    "data": status_update
                }
            )
            
            # Check if complete
            if project.status in ["ready", "failed"]:
                break
                
            await asyncio.sleep(5)
            
        # Handle timeout
        if project.status not in ["ready", "failed"]:
            await project_service.update_project(
                project_id,
                {"status": "failed", "error": "Project creation timed out"}
            )
            
    except Exception as e:
        # Handle monitoring failure
        try:
            await redis.set(
                status_key,
                {
                    "status": "failed",
                    "error": str(e),
                    "last_update": datetime.utcnow().isoformat()
                }
            )
            await project_service.update_project(
                project_id,
                {"status": "failed", "error": str(e)}
            )
        except Exception:
            pass  # Prevent monitoring errors from cascading 