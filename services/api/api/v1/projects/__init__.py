"""Project management endpoints."""

from typing import List, Optional
from uuid import UUID

from api.dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from services.project_service import ProjectService
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.models.user import User

from .agents import router as agents_router
from .events import router as events_router
from .teams import router as teams_router

router = APIRouter(prefix="/projects", tags=["projects"])

# Include sub-routers
router.include_router(agents_router)
router.include_router(events_router)
router.include_router(teams_router)


@router.post("", response_model=APIResponse[ProjectResponse])
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """Create a new project."""
    try:
        service = ProjectService(db)
        result = await service.create_project(project, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PROJECT_CREATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("", response_model=APIResponse[List[ProjectResponse]])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[ProjectResponse]]:
    """List all projects with optional search and pagination."""
    try:
        service = ProjectService(db)
        projects = await service.list_projects(skip, limit, search, current_user.id)

        return APIResponse(success=True, data=projects)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PROJECT_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """Get a specific project by ID."""
    try:
        service = ProjectService(db)
        project = await service.get_project(project_id, current_user.id)

        return APIResponse(success=True, data=project)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PROJECT_GET_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.put("/{project_id}", response_model=APIResponse[ProjectResponse])
async def update_project(
    project_id: UUID,
    project: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """Update a specific project."""
    try:
        service = ProjectService(db)
        result = await service.update_project(project_id, project, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PROJECT_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.delete("/{project_id}", response_model=APIResponse[bool])
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """Delete a specific project."""
    try:
        service = ProjectService(db)
        result = await service.delete_project(project_id, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PROJECT_DELETE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )
