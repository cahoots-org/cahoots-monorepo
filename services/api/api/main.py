"""Main application router."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from api.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    service_error_handler,
    base_error_handler
)
from api.v1 import router as v1_router
from utils.config import get_settings
from core.exceptions import (
    BaseError,
    ServiceError
)
from api.middleware.request_tracking import RequestTrackingMiddleware

def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Cahoots Service",
        description="API for Cahoots service",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Add request tracking
    app.add_middleware(RequestTrackingMiddleware)

    # Register error handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(BaseError, base_error_handler)

    # Register v1 router
    app.include_router(v1_router)

    return app

app = create_app()