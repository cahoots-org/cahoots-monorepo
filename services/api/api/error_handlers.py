"""Error handler middleware for consistent error handling."""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import logging
from typing import Any, Dict

from core.exceptions import (
    BaseError,
    ServiceError,
    ValidationError,
    AuthError,
    DomainError,
    InfrastructureError,
    ErrorCategory,
    ErrorSeverity
)
from schemas.base import APIResponse, ErrorDetail

logger = logging.getLogger(__name__)

async def base_error_handler(request: Request, exc: BaseError) -> JSONResponse:
    """Handle base application errors.
    
    Args:
        request: Request instance
        exc: Exception instance
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=_get_status_code(exc.category),
        content=APIResponse(
            success=False,
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                category=exc.category,
                severity=exc.severity,
                details=exc.details
            ).dict()
        ).dict()
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: Request instance
        exc: Exception instance
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            error=ErrorDetail(
                code="HTTP_ERROR",
                message=str(exc.detail),
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.ERROR
            ).dict()
        ).dict()
    )

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.
    
    Args:
        request: Request instance
        exc: Exception instance
        
    Returns:
        JSON response with error details
    """
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content=APIResponse(
            success=False,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.WARNING,
                details={"errors": errors}
            ).dict()
        ).dict()
    )

async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Handle service-specific errors.
    
    Args:
        request: Request instance
        exc: Exception instance
        
    Returns:
        JSON response with error details
    """
    return await base_error_handler(request, exc)

def _get_status_code(category: ErrorCategory) -> int:
    """Get HTTP status code for error category.
    
    Args:
        category: Error category
        
    Returns:
        HTTP status code
    """
    status_codes = {
        ErrorCategory.VALIDATION: 422,
        ErrorCategory.AUTHENTICATION: 401,
        ErrorCategory.AUTHORIZATION: 403,
        ErrorCategory.BUSINESS_LOGIC: 400,
        ErrorCategory.INFRASTRUCTURE: 500,
        ErrorCategory.EXTERNAL_SERVICE: 502
    }
    return status_codes.get(category, 500)