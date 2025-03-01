from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os

from ..domain.events import Event, EventMetadata
from ..infrastructure.event_store import EventStore
from ..infrastructure.view_store import InMemoryViewStore
from ..application.handlers import ProjectHandler
from ..application.organization_handler import OrganizationHandler
from ..domain.auth.handler import AuthHandler
from ..domain.code_changes.handler import CodeChangesHandler

from .middleware.rate_limit import RateLimiter
from .middleware.auth import AuthMiddleware
from .webhooks import WebhookManager
from . import status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Dev Team API",
    description="Event-sourced API for AI development team management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize stores
event_store = EventStore()
view_store = InMemoryViewStore()

# Initialize handlers
project_handler = ProjectHandler(event_store, view_store)
organization_handler = OrganizationHandler(event_store, view_store)
auth_handler = AuthHandler(event_store, view_store)
code_changes_handler = CodeChangesHandler(event_store, view_store)

# Set up code changes handler
project_handler.set_code_changes_handler(code_changes_handler)

# Initialize middleware
rate_limiter = RateLimiter(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    rate_limit_per_day=int(os.getenv("RATE_LIMIT_PER_DAY", "10000"))
)

auth_middleware = AuthMiddleware(
    secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key"),
    algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
)

# Initialize webhook manager
webhook_manager = WebhookManager(event_store, view_store)

# Add middleware
app.middleware("http")(rate_limiter)
app.middleware("http")(auth_middleware)

# Import and include routers
from .routers import auth, organizations, projects, teams
from . import webhooks

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(status.router, prefix="/api/v1/status", tags=["status"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Make handlers and services available to routes
@app.middleware("http")
async def inject_dependencies(request: Request, call_next):
    """Inject dependencies into request state"""
    request.state.event_store = event_store
    request.state.view_store = view_store
    request.state.project_handler = project_handler
    request.state.organization_handler = organization_handler
    request.state.auth_handler = auth_handler
    request.state.code_changes_handler = code_changes_handler
    request.state.webhook_manager = webhook_manager
    response = await call_next(request)
    return response 