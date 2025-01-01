"""Global exception handlers for the API."""
from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Union, Dict, Any
from src.utils.logger import Logger
from src.utils.exceptions import BaseAppException

# Initialize logger
logger = Logger("API-Errors")

def register_error_handlers(app: FastAPI) -> None:
    """Register global error handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )
    app.add_exception_handler(
        ValidationError,
        validation_exception_handler
    )
    app.add_exception_handler(
        BaseAppException,
        app_exception_handler
    )
    app.add_exception_handler(
        Exception,
        internal_exception_handler
    )

async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle validation errors from FastAPI and Pydantic.
    
    Args:
        request: The request that caused the error
        exc: The validation error
        
    Returns:
        JSONResponse with error details
    """
    errors = []
    for error in exc.errors():
        error_location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "location": error_location,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.error(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors=errors,
        client_host=request.client.host,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "detail": "Validation error",
            "errors": errors
        }
    )

async def app_exception_handler(
    request: Request,
    exc: BaseAppException
) -> JSONResponse:
    """
    Handle application-specific exceptions.
    
    Args:
        request: The request that caused the error
        exc: The application exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(
        exc.message,
        path=request.url.path,
        method=request.method,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details,
        client_host=request.client.host,
        request_id=request.headers.get("X-Request-ID"),
        exc_info=True if exc.status_code >= 500 else False
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.message,
            "details": exc.details
        }
    )

async def http_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: The request that caused the error
        exc: The HTTP exception
        
    Returns:
        JSONResponse with error details
    """
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail = str(exc)
    
    logger.error(
        "HTTP error",
        path=request.url.path,
        method=request.method,
        status_code=status_code,
        detail=detail,
        client_host=request.client.host,
        request_id=request.headers.get("X-Request-ID"),
        exc_info=True if status_code >= 500 else False
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": "HTTP_ERROR",
            "detail": detail
        }
    )

async def internal_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle any unhandled exceptions.
    
    Args:
        request: The request that caused the error
        exc: The unhandled exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(
        "Internal server error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        client_host=request.client.host,
        request_id=request.headers.get("X-Request-ID"),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "detail": "Internal server error",
            "error_type": type(exc).__name__
        }
    ) 