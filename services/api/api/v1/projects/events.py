"""Project event management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.events import EventCreate, EventResponse
from services.event_service import EventService
from cahoots_core.models.user import User

router = APIRouter(prefix="/{project_id}/events", tags=["project-events"])

@router.post("", response_model=APIResponse[EventResponse])
async def create_event(
    project_id: UUID,
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[EventResponse]:
    """Create a new project event."""
    try:
        service = EventService(db)
        result = await service.create_event(project_id, event, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="EVENT_CREATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("", response_model=APIResponse[List[EventResponse]])
async def list_events(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[EventResponse]]:
    """List project events with pagination."""
    try:
        service = EventService(db)
        events = await service.list_events(project_id, skip, limit)
        
        return APIResponse(
            success=True,
            data=events
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="EVENT_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: UUID,
    token: str
):
    """WebSocket endpoint for real-time project events."""
    try:
        await websocket.accept()
        service = EventService()
        await service.handle_websocket(websocket, project_id, token)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))