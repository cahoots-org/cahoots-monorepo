"""Project management API endpoints."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from src.services.project_service import ProjectService
from src.schemas.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectsResponse,
    AgentDeployment,
    AgentConfig
)
from src.api.deps import get_current_organization, get_project_service
from src.utils.monitoring import monitor_project_creation

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    organization_id: UUID = Depends(get_current_organization),
    project_service: ProjectService = Depends(get_project_service)
):
    """Create a new project.
    
    This endpoint initiates project creation and returns immediately with a response
    containing links to monitor progress. The actual resource creation continues
    in the background.
    
    Returns a ProjectResponse with HATEOAS links to:
    - Project API endpoint
    - GitHub repository (when ready)
    - Documentation (when ready)
    - Monitoring dashboard
    - Logging dashboard
    - Other project artifacts
    """
    try:
        # Create project and get initial response
        project_response = await project_service.create_project(
            organization_id=organization_id,
            project_data=project_data
        )
        
        # Add background task to monitor project creation
        background_tasks.add_task(
            monitor_project_creation,
            project_id=project_response.id,
            organization_id=organization_id
        )
        
        return project_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("", response_model=ProjectsResponse)
async def list_projects(
    organization_id: UUID = Depends(get_current_organization),
    service: ProjectService = Depends(get_project_service)
):
    """List all projects for organization."""
    projects = await service.list_projects(organization_id)
    return ProjectsResponse(
        total=len(projects),
        projects=[ProjectResponse.from_orm(p) for p in projects]
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service)
):
    """Get project by ID."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.from_orm(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update: ProjectUpdate,
    service: ProjectService = Depends(get_project_service)
):
    """Update project."""
    project = await service.update_project(
        project_id=project_id,
        name=update.name,
        description=update.description,
        agent_config=update.agent_config,
        resource_limits=update.resource_limits
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.from_orm(project)

@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service)
):
    """Delete project."""
    deleted = await service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success"}

@router.post("/{project_id}/agents", response_model=AgentDeployment)
async def deploy_agent(
    project_id: UUID,
    config: AgentConfig,
    service: ProjectService = Depends(get_project_service)
):
    """Deploy an agent for the project."""
    try:
        status = await service.deploy_agent(
            project_id=project_id,
            agent_type=config.agent_type,
            config=config.config
        )
        return AgentDeployment(
            agent_type=config.agent_type,
            status=status
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{project_id}/agents/{agent_type}/scale")
async def scale_agent(
    project_id: UUID,
    agent_type: str,
    replicas: int,
    service: ProjectService = Depends(get_project_service)
):
    """Scale an agent deployment."""
    try:
        status = await service.scale_agent(
            project_id=project_id,
            agent_type=agent_type,
            replicas=replicas
        )
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{project_id}/agents/{agent_type}")
async def delete_agent(
    project_id: UUID,
    agent_type: str,
    service: ProjectService = Depends(get_project_service)
):
    """Delete an agent deployment."""
    try:
        await service.delete_agent(
            project_id=project_id,
            agent_type=agent_type
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 