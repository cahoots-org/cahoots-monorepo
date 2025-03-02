"""Project management API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from api.dependencies import (
    ServiceDeps,
    get_current_organization,
    get_current_user,
    get_db,
    get_project_service,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from schemas.project import AgentConfig, AgentDeployment
from schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectsResponse,
    ProjectUpdate,
)
from services.project_service import ProjectService
from utils.monitoring import monitor_project_creation

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    organization_id: UUID = Depends(get_current_organization),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Create a new project.

    This endpoint initiates project creation and returns immediately with a response
    containing links to monitor progress. The actual resource creation continues
    in the background.

    Args:
        project_data: Project creation data
        background_tasks: FastAPI background tasks
        organization_id: Current organization ID
        project_service: Project service instance

    Returns:
        ProjectResponse with HATEOAS links to:
        - Project API endpoint
        - GitHub repository (when ready)
        - Documentation (when ready)
        - Monitoring dashboard
        - Logging dashboard

    Raises:
        HTTPException: If project creation fails
    """
    try:
        # Create project and get initial response
        project_response = await project_service.create_project(
            organization_id=organization_id, project_data=project_data
        )

        # Add background task to monitor project creation
        background_tasks.add_task(
            monitor_project_creation,
            project_id=project_response.id,
            organization_id=organization_id,
        )

        return project_response

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.get("", response_model=ProjectsResponse)
async def list_projects(
    organization_id: UUID = Depends(get_current_organization),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectsResponse:
    """
    List all projects for organization.

    Args:
        organization_id: Current organization ID
        project_service: Project service instance

    Returns:
        List of projects with total count

    Raises:
        HTTPException: If listing projects fails
    """
    try:
        projects = await project_service.list_projects(organization_id)
        return ProjectsResponse(
            total=len(projects), projects=[ProjectResponse.from_orm(p) for p in projects]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, project_service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Get project by ID.

    Args:
        project_id: Project identifier
        project_service: Project service instance

    Returns:
        Project details

    Raises:
        HTTPException: If project not found or retrieval fails
    """
    try:
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}",
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Update project.

    Args:
        project_id: Project identifier
        update: Project update data
        project_service: Project service instance

    Returns:
        Updated project details

    Raises:
        HTTPException: If project not found or update fails
    """
    try:
        project = await project_service.update_project(
            project_id=project_id,
            name=update.name,
            description=update.description,
            agent_config=update.agent_config,
            resource_limits=update.resource_limits,
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID, project_service: ProjectService = Depends(get_project_service)
) -> None:
    """
    Delete project.

    Args:
        project_id: Project identifier
        project_service: Project service instance

    Raises:
        HTTPException: If project not found or deletion fails
    """
    try:
        deleted = await project_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )


@router.post("/{project_id}/agents", response_model=AgentDeployment)
async def deploy_agent(
    project_id: UUID,
    config: AgentConfig,
    project_service: ProjectService = Depends(get_project_service),
) -> AgentDeployment:
    """
    Deploy an agent for the project.

    Args:
        project_id: Project identifier
        config: Agent configuration
        project_service: Project service instance

    Returns:
        Agent deployment status

    Raises:
        HTTPException: If deployment fails
    """
    try:
        status = await project_service.deploy_agent(
            project_id=project_id, agent_type=config.agent_type, config=config.config
        )
        return AgentDeployment(agent_type=config.agent_type, status=status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{project_id}/agents/{agent_type}/scale", response_model=Dict[str, Any])
async def scale_agent(
    project_id: UUID,
    agent_type: str,
    replicas: int,
    project_service: ProjectService = Depends(get_project_service),
) -> Dict[str, Any]:
    """
    Scale an agent deployment.

    Args:
        project_id: Project identifier
        agent_type: Type of agent to scale
        replicas: Number of replicas
        project_service: Project service instance

    Returns:
        Scaling operation status

    Raises:
        HTTPException: If scaling fails
    """
    try:
        status = await project_service.scale_agent(
            project_id=project_id, agent_type=agent_type, replicas=replicas
        )
        return {"status": status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scale agent: {str(e)}",
        )


@router.delete("/{project_id}/agents/{agent_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    project_id: UUID,
    agent_type: str,
    project_service: ProjectService = Depends(get_project_service),
) -> None:
    """
    Delete an agent deployment.

    Args:
        project_id: Project identifier
        agent_type: Type of agent to delete
        project_service: Project service instance

    Raises:
        HTTPException: If deletion fails
    """
    try:
        await project_service.delete_agent(project_id=project_id, agent_type=agent_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}",
        )
