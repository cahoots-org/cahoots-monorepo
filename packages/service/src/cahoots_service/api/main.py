"""Main application router."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from cahoots_service.api.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    service_error_handler
)
from cahoots_service.api.auth import router as auth_router
from cahoots_service.api.projects import router as projects_router
from cahoots_service.api.billing import router as billing_router
from cahoots_service.api.metrics import router as metrics_router
from cahoots_service.api.health import router as health_router
from cahoots_service.utils.config import get_settings
from cahoots_core.exceptions import ServiceError

def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Cahoots Service",
        description="API for Cahoots service",
        version="0.1.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register error handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ServiceError, service_error_handler)

    # Register routers
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(billing_router)
    app.include_router(metrics_router)
    app.include_router(health_router)

    return app

app = create_app()