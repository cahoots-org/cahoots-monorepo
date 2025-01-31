"""Project management endpoints."""
from typing import Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from cahoots_core.models.project import ProjectCreate, Project
from cahoots_core.models.db_models import Organization
from cahoots_service.api.dependencies import ServiceDeps, get_db, get_event_bus
from cahoots_service.schemas.project import ProjectResponse
from cahoots_service.api.auth import verify_api_key
from cahoots_service.services.project_service import ProjectService
from cahoots_service.utils.config import get_settings
from cahoots_core.exceptions.domain import DomainError
from cahoots_core.exceptions.infrastructure import InfrastructureError

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    deps: ServiceDeps = Depends(ServiceDeps),
    organization_id: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Create a new project.
    
    Args:
        project: Project details
        deps: Service dependencies
        organization_id: Organization ID from API key
        
    Returns:
        Dict[str, Any]: Created project details
        
    Raises:
        HTTPException: If project creation fails
    """
    try:
        # Verify organization exists
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await deps.db.execute(stmt)
        org = await result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
            
        # Check project name uniqueness within organization
        stmt = select(Project).where(
            Project.organization_id == organization_id,
            Project.name == project.name
        )
        result = await deps.db.execute(stmt)
        existing_project = await result.scalar_one_or_none()
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name already exists in organization"
            )
            
        # Create project
        project_service = ProjectService(deps)
        new_project = await project_service.create_project(
            name=project.name,
            description=project.description,
            organization_id=organization_id,
            agent_config=project.agent_config,
            resource_limits=project.resource_limits
        )
        
        # Commit changes
        await deps.db.commit()
        
        return {
            "id": str(new_project.id),
            "name": new_project.name,
            "description": new_project.description,
            "created_at": new_project.created_at.isoformat(),
            "status": new_project.status,
            "agent_config": new_project.agent_config,
            "resource_limits": new_project.resource_limits
        }
            
    except HTTPException:
        await deps.db.rollback()
        raise
    except Exception as e:
        await deps.db.rollback()
        # Log the error for debugging
        import logging
        logging.error(f"Failed to create project: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project. Please try again later."
        ) 