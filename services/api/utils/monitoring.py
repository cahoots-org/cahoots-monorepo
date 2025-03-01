"""Monitoring utilities for service operations."""
import asyncio
import logging
from typing import Optional
from uuid import UUID

from services.project_service import ProjectService

logger = logging.getLogger(__name__)

async def monitor_project_creation(
    project_id: UUID,
    organization_id: UUID,
    max_retries: int = 30,
    retry_delay: int = 10
) -> None:
    """
    Monitor project creation progress.
    
    This function runs in the background and monitors the status of project creation,
    including repository setup, agent deployments, and other initialization tasks.
    
    Args:
        project_id: Project identifier
        organization_id: Organization identifier
        max_retries: Maximum number of status check attempts
        retry_delay: Delay between status checks in seconds
    """
    project_service = ProjectService()
    retries = 0
    
    while retries < max_retries:
        try:
            project = await project_service.get_project(project_id)
            if not project:
                logger.error(f"Project {project_id} not found during monitoring")
                return
                
            # Check if all initialization tasks are complete
            if project.status == "ready":
                logger.info(f"Project {project_id} creation completed successfully")
                return
                
            # Check for failed state
            if project.status == "failed":
                logger.error(f"Project {project_id} creation failed")
                return
                
            # Continue monitoring
            logger.debug(f"Project {project_id} status: {project.status}")
            retries += 1
            await asyncio.sleep(retry_delay)
            
        except Exception as e:
            logger.error(f"Error monitoring project {project_id}: {str(e)}")
            return
            
    logger.warning(f"Project {project_id} monitoring timed out after {max_retries} retries") 