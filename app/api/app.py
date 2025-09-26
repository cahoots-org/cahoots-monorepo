"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import task_router, health_router, websocket_router, epics_router, auth_router
from app.api.dependencies import cleanup_dependencies


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    print("Starting Cahoots Monolith API...")
    yield
    # Shutdown
    print("Shutting down...")
    await cleanup_dependencies()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cahoots Task Manager",
        description="Optimized monolith for recursive task decomposition",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    # Configure allowed origins based on environment
    import os
    environment = os.environ.get("ENVIRONMENT", "development")

    if environment == "production":
        allowed_origins = [
            "https://cahoots-frontend.fly.dev",
            "https://cahoots.fly.dev"
        ]
    else:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000"
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(task_router)
    app.include_router(epics_router)
    app.include_router(websocket_router)
    app.include_router(auth_router)

    # Include integration routers - import here to avoid circular imports
    from app.integrations import jira_router, trello_router, github_router
    app.include_router(jira_router)
    app.include_router(trello_router)
    app.include_router(github_router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "Cahoots Task Manager",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "tasks": "/api/tasks",
                "epics": "/api/epics",
                "websocket": "/ws/global",
                "auth": "/api/auth",
                "jira": "/api/jira",
                "trello": "/api/trello",
                "github": "/api/github",
                "docs": "/docs",
                "openapi": "/openapi.json"
            }
        }

    return app