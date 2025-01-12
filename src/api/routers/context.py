from typing import Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.services.context_service import ContextEventService
from src.utils.version_vector import VersionVector
from src.schemas.context import (
    ContextEventCreate,
    ContextEventResponse,
    ContextResponse,
    VersionVectorResponse
)

router = APIRouter(prefix="/api/context", tags=["context"])

@router.post("/{project_id}/events", response_model=ContextEventResponse)
async def append_event(
    project_id: UUID,
    event: ContextEventCreate,
    db: Session = Depends(get_db)
):
    """
    Append a new event to the project's context history.
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
    """
    context_service = ContextEventService(db)
    
    try:
        context = await context_service.get_context(project_id)
        vector = await context_service.get_version_vector(project_id)
        return ContextResponse(
            context=context,
            version_vector=vector.vector
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
    """
    context_service = ContextEventService(db)
    
    try:
        vector = await context_service.get_version_vector(project_id)
        return VersionVectorResponse(
            version_vector=vector.vector,
            timestamp=vector.timestamp
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 