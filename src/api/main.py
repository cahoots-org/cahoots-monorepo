"""Main API module."""
import json
import logging
import time
from typing import Dict, Optional, Annotated
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from ..models.project import Project
from ..models.story import Story
from ..utils.base_logger import BaseLogger
from ..utils.metrics import http_request_duration_seconds as request_latency
from ..utils.metrics import http_requests_total as request_count
from .auth import verify_api_key
from .core import get_event_system
from .error_handlers import register_error_handlers
from .health import get_health_check
from .metrics import get_metrics
from .core import EventSystem

# Initialize FastAPI app
app = FastAPI(
    title="AI Dev Team API",
    description="API for managing AI development team workflows",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = BaseLogger(__name__)

# Register error handlers
register_error_handlers(app)

# Add request tracking middleware
class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking request metrics."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Track request metrics."""
        request_id = request.headers.get("X-Request-ID", "unknown")
        start_time = time.time()
        
        response = await call_next(request)
        
        # Record request duration
        duration = time.time() - start_time
        request_latency.labels(
            path=request.url.path,
            method=request.method
        ).observe(duration)
        
        # Record request count
        request_count.labels(
            path=request.url.path,
            method=request.method,
            status=response.status_code
        ).inc()
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestTrackingMiddleware)

@app.get("/health")
async def health_check(
    response: Response,
    event_system: Annotated[EventSystem, Depends(get_event_system)]
) -> Dict:
    """Health check endpoint."""
    return await get_health_check(response, event_system)

@app.get("/metrics")
def metrics() -> StarletteResponse:
    """Prometheus metrics endpoint."""
    return get_metrics()

@app.post("/projects")
async def create_project(
    project: Project,
    api_key: str = Depends(verify_api_key)
) -> Dict:
    """Create a new project."""
    logger.info(f"Creating project: {project.model_dump()}")
    try:
        event_system = get_event_system()
        await event_system.publish("projects", project.model_dump())
        return {
            "id": project.id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )

@app.post("/stories")
async def create_story(
    story: Story,
    api_key: str = Depends(verify_api_key)
) -> Dict:
    """Create a new story."""
    logger.info(f"Creating story: {story.model_dump()}")
    try:
        event_system = get_event_system()
        await event_system.publish("stories", story.model_dump())
        return {
            "id": story.id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to create story: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create story: {str(e)}"
        )