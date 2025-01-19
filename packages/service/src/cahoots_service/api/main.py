"""Main FastAPI application."""
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.core.config import get_settings, SecurityConfig
from src.core.dependencies import get_security_manager
from src.utils.redis import create_redis_client
from .middleware.request_tracking import add_request_id
from .middleware.security import SecurityMiddleware
from .auth import router as auth_router
from .health import router as health_router
from .metrics import router as metrics_router
from .organizations import router as organizations_router
from .projects import router as projects_router
from .webhook import router as webhook_router
from .billing import router as billing_router

app = FastAPI(title="Cahoots API")

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(add_request_id)

# Initialize security middleware
security_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize app dependencies on startup."""
    global security_manager
    redis = await create_redis_client()
    security_manager = await get_security_manager(redis=redis, config=SecurityConfig())

# Add security middleware with placeholder manager
app.add_middleware(SecurityMiddleware, security_manager=None)

# Add routers
app.include_router(auth_router, prefix="/auth")
app.include_router(health_router, prefix="/health")
app.include_router(metrics_router, prefix="/metrics")
app.include_router(organizations_router, prefix="/api/organizations")
app.include_router(projects_router, prefix="/api/projects")
app.include_router(webhook_router, prefix="/webhooks")
app.include_router(billing_router, prefix="/billing")