"""Context Manager Service for Cahoots

This service manages context and knowledge for the Cahoots AI development team.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cahoots_core.utils.infrastructure.redis.client import get_redis_client
from cahoots_events.bus.system import EventSystem
from cahoots_events.models.events import Event, EventStatus, EventPriority
from cahoots_context.storage.context_service import ContextEventService
from cahoots_context.manager.project import project_context

# Create the FastAPI application
app = FastAPI(
    title="Context Manager Service",
    description="Manages context and knowledge for the Cahoots platform",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be configured properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
redis_client = get_redis_client()
event_system = EventSystem(redis_client)
context_service = ContextEventService()

# Create router for health checks
health_router = APIRouter(tags=["Health"])

@health_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "context-manager",
        "version": "0.1.0"
    }

# Create router for context operations
context_router = APIRouter(prefix="/context", tags=["Context"])

class ContextEventCreate(BaseModel):
    """Schema for creating context events."""
    event_type: str
    event_data: Dict[str, Any]
    version_vector: Optional[Dict[str, int]] = None

@context_router.get("/{project_id}")
async def get_context(project_id: UUID):
    """Get current context for a project."""
    try:
        context = await context_service.get_context(project_id)
        vector = await context_service.get_version_vector(project_id)
        return {
            "context": context,
            "version_vector": vector.agent_versions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@context_router.post("/{project_id}/events")
async def create_context_event(project_id: UUID, event: ContextEventCreate):
    """Create a new context event."""
    try:
        # Store event in context service
        stored_event = await context_service.append_event(
            project_id=project_id,
            event_type=event.event_type,
            event_data=event.event_data,
            version_vector=event.version_vector
        )
        
        # Publish event to event system
        await event_system.publish(Event(
            id=stored_event.id,
            project_id=project_id,
            type=f"context.{event.event_type}",
            status=EventStatus.PENDING,
            priority=EventPriority.HIGH,
            data={
                "event_type": event.event_type,
                "event_data": event.event_data,
                "version_vector": stored_event.version_vector
            }
        ))
        
        return stored_event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Event handlers
@event_system.subscribe("context.*")
async def handle_context_event(event: Event):
    """Handle incoming context events."""
    async with project_context(str(event.project_id)) as ctx:
        await context_service.apply_event_to_context(
            ctx.context,
            event.data
        )

# Include routers
app.include_router(health_router)
app.include_router(context_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
