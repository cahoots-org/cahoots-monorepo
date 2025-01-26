"""Error handlers for the API."""
from logging import Logger
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from cahoots_core.exceptions import (
    CahootsError,
    APIError,
    ValidationError,
    ErrorCategory,
    ErrorSeverity,
    ServiceError
)

logger = Logger("api.error_handlers")

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: Request instance
        exc: HTTP exception
        
    Returns:
        JSONResponse: Error response
    """
    error_response = {
        "success": False,
        "detail": str(exc.detail),
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "category": ErrorCategory.API.value,
            "severity": ErrorSeverity.ERROR.value
        }
    }
    
    logger.error(
        f"HTTP error {exc.status_code}: {exc.detail}",
        extra={"path": request.url.path}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.
    
    Args:
        request: Request instance
        exc: Validation exception
        
    Returns:
        JSONResponse: Error response
    """
    error_details = []
    for error in exc.errors():
        loc = error.get("loc", [])
        if len(loc) > 1:
            field = loc[-1]  # Get the last item as the field name
        else:
            field = " -> ".join(str(x) for x in loc)
            
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = {
        "success": False,
        "detail": "Request validation failed",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": error_details,
            "category": ErrorCategory.VALIDATION.value,
            "severity": ErrorSeverity.WARNING.value
        }
    }
    
    logger.error(
        "Validation error",
        extra={
            "path": request.url.path,
            "errors": error_details
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )

async def app_exception_handler(
    request: Request,
    exc: CahootsError
) -> JSONResponse:
    """Handle application-specific exceptions.
    
    Args:
        request: Request instance
        exc: Application exception
        
    Returns:
        JSONResponse: Error response
    """
    error_response = {
        "success": False,
        "detail": str(exc),
        "error": exc.to_dict()
    }
    
    logger.error(
        str(exc),
        extra={
            "path": request.url.path,
            "error_code": exc.code,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code if hasattr(exc, 'status_code') else status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )

async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Handle service-specific errors.
    
    Args:
        request: Request instance
        exc: Service error
        
    Returns:
        JSONResponse: Error response
    """
    error_response = {
        "success": False,
        "detail": str(exc),
        "error": {
            "code": exc.code,
            "message": str(exc),
            "details": exc.details,
            "service": exc.details.get("service"),
            "operation": exc.details.get("operation"),
            "category": ErrorCategory.INFRASTRUCTURE.value,
            "severity": ErrorSeverity.ERROR.value
        }
    }
    
    logger.error(
        f"Service error: {exc}",
        extra={
            "path": request.url.path,
            "service": exc.details.get("service"),
            "operation": exc.details.get("operation")
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    error_response = {
        "success": False,
        "detail": str(exc),
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "details": {
                "type": exc.__class__.__name__,
                "message": str(exc)
            },
            "category": ErrorCategory.INFRASTRUCTURE.value,
            "severity": ErrorSeverity.ERROR.value
        }
    }
    
    logger.error(
        f"Unhandled error: {exc}",
        extra={
            "path": request.url.path,
            "error_type": exc.__class__.__name__
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )

def register_error_handlers(app):
    """Register error handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(CahootsError, app_exception_handler)
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)