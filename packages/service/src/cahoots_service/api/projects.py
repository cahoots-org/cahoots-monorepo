"""Project management endpoints."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.api.dependencies import get_db, get_verified_event_system
from src.database.models import Project, Organization
from src.utils.models import ProjectResponse
from src.api.auth import verify_api_key
from src.services.project_service import ProjectService
from src.core.dependencies import BaseDeps
from src.utils.config import get_settings

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    """Project creation request model."""
    name: constr(min_length=1, max_length=100)
    description: str

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    deps: BaseDeps = Depends(BaseDeps),
    organization_id: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Create a new project.
    
    Args:
        project: Project details
        deps: Base dependencies
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
            organization_id=organization_id
        )
        
        # Commit changes
        await deps.db.commit()
        
        return {
            "id": str(new_project.id),
            "name": new_project.name,
            "description": new_project.description,
            "created_at": new_project.created_at.isoformat(),
            "status": new_project.status
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