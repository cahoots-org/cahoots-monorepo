"""Context router for managing project context."""
from typing import Dict
from uuid import UUID
from cahoots_core.utils.version_vector import VersionVector
from api.dependencies import get_db
from schemas.context import (
    ContextEventCreate,
    ContextEventResponse,
    ContextResponse,
    VersionVectorResponse
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.cahoots_context.storage.context_service import ContextEventService

router = APIRouter(prefix="/api/context", tags=["context"])

@router.post("/{project_id}/events", response_model=ContextEventResponse)
async def append_event(
    project_id: UUID,
    event: ContextEventCreate,
    db: Session = Depends(get_db)
):
    """
    Append a new event to the project's context history.
    
    Args:
        project_id: The project identifier
        event: The event to append
        db: Database session
        
    Returns:
        The created context event
    """
    context_service = ContextEventService(db)
    vector = VersionVector(event.version_vector) if event.version_vector else None
    
    try:
        event = await context_service.append_event(
            project_id=project_id,
            event_type=event.event_type,
            event_data=event.event_data,
            version_vector=vector
        )
        return event
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}", response_model=ContextResponse)
async def get_context(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the current context for a project.
    
    Args:
        project_id: The project identifier
        db: Database session
        
    Returns:
        The current context state and version vector
    """
    context_service = ContextEventService(db)
    
    try:
        context = await context_service.get_context(project_id)
        vector = await context_service.get_version_vector(project_id)
        return ContextResponse(
            context=context,
            version_vector=vector.versions
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/vector", response_model=VersionVectorResponse)
async def get_version_vector(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the current version vector for a project.
    
    Args:
        project_id: The project identifier
        db: Database session
        
    Returns:
        The current version vector and timestamp
    """
    context_service = ContextEventService(db)
    
    try:
        vector = await context_service.get_version_vector(project_id)
        return VersionVectorResponse(
            version_vector=vector.versions,
            timestamp=vector.timestamp
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 