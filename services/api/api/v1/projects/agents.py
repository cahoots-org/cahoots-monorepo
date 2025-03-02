"""Project agent management endpoints."""

from typing import Any, Dict
from uuid import UUID

from api.dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.agents import AgentDeployment, AgentScaleRequest
from schemas.base import APIResponse, ErrorCategory, ErrorDetail, ErrorSeverity
from services.agent_service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession

from cahoots_core.models.user import User

router = APIRouter(prefix="/{project_id}/agents", tags=["project-agents"])


@router.post("", response_model=APIResponse[AgentDeployment])
async def deploy_agent(
    project_id: UUID,
    deployment: AgentDeployment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[AgentDeployment]:
    """Deploy an agent to a project."""
    try:
        service = AgentService(db)
        result = await service.deploy_agent(project_id, deployment, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AGENT_DEPLOY_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.patch("/{agent_type}/scale", response_model=APIResponse[Dict[str, Any]])
async def scale_agent(
    project_id: UUID,
    agent_type: str,
    scale_request: AgentScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """Scale agent instances."""
    try:
        service = AgentService(db)
        result = await service.scale_agent(
            project_id, agent_type, scale_request.replicas, current_user.id
        )

        return APIResponse(success=True, data={"replicas": result})
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AGENT_SCALE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )


@router.delete("/{agent_type}", response_model=APIResponse[bool])
async def remove_agent(
    project_id: UUID,
    agent_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """Remove an agent from a project."""
    try:
        service = AgentService(db)
        result = await service.remove_agent(project_id, agent_type, current_user.id)

        return APIResponse(success=True, data=result)
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AGENT_REMOVE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR,
            ),
        )
