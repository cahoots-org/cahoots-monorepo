"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import (
    task_router,
    health_router,
    websocket_router,
    epics_router,
    auth_router,
    events_router,
    cascade_router,
    user_settings_router,
    metrics_router,
    projects_router
)
from app.api.dependencies import cleanup_dependencies


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    print("Starting Cahoots Monolith API...")

    # Initialize Context Engine (only if not disabled)
    import os
    if os.getenv("DISABLE_CONTEXT_ENGINE", "false").lower() != "true":
        try:
            from app.api.dependencies import get_context_engine_client
            await get_context_engine_client()
            print("✓ Context Engine initialized")
        except Exception as e:
            print(f"⚠ Context Engine initialization failed: {e}")
            print("  Continuing without Context Engine...")

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

    # Custom middleware to ensure CORS headers on ALL responses including 500 errors
    class CORSErrorMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            try:
                response = await call_next(request)
            except Exception as e:
                # Handle any unhandled exception
                import traceback
                origin = request.headers.get("origin")
                headers = {}
                if origin in allowed_origins:
                    headers = {
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*",
                    }
                # Log the actual error
                print(f"[MIDDLEWARE] Unhandled exception: {type(e).__name__}: {str(e)}")
                print(f"[MIDDLEWARE] Traceback: {traceback.format_exc()}")

                # Return a 500 error with CORS headers AND the actual error for debugging
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"{type(e).__name__}: {str(e)}"},
                    headers=headers
                )

            # For successful responses, ensure CORS headers are present
            origin = request.headers.get("origin")
            if origin in allowed_origins and response.status_code >= 400:
                # Add CORS headers if not already present on error responses
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"

            return response

    # Add custom middleware first
    app.add_middleware(CORSErrorMiddleware)

    # Then add standard CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom exception handler to include CORS headers in error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Custom exception handler that includes CORS headers."""
        origin = request.headers.get("origin")
        headers = {}

        # Add CORS headers if origin is allowed
        if origin in allowed_origins:
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers
        )

    # Include routers
    app.include_router(health_router)
    app.include_router(task_router)
    app.include_router(epics_router)
    app.include_router(websocket_router)
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(cascade_router)
    app.include_router(user_settings_router)
    app.include_router(metrics_router)
    app.include_router(projects_router)

    # Include utility routers
    from app.api.routes import regenerate_router
    app.include_router(regenerate_router, prefix="/api")

    # Include integration routers - import here to avoid circular imports
    from app.integrations import jira_router, trello_router, github_router
    app.include_router(jira_router)
    app.include_router(trello_router)
    app.include_router(github_router)

    # Include blog routers
    from app.api.routes.blog import admin_router as blog_admin_router
    from app.api.routes.blog import public_router as blog_public_router
    from app.api.routes.blog import upload_router
    app.include_router(blog_admin_router, prefix="/api")
    app.include_router(blog_public_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")

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
                "settings": "/api/settings",
                "jira": "/api/jira",
                "trello": "/api/trello",
                "github": "/api/github",
                "docs": "/docs",
                "openapi": "/openapi.json"
            }
        }

    return app