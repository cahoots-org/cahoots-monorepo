"""Error handlers for the API."""
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from src.utils.exceptions import BaseError
from src.utils.logger import Logger

logger = Logger("api.error_handlers")

def register_error_handlers(app):
    """Register error handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(HTTPException)
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
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "status_code": exc.status_code
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
    
    @app.exception_handler(RequestValidationError)
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
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": error_details
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
    
    @app.exception_handler(BaseError)
    async def app_exception_handler(
        request: Request,
        exc: BaseError
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
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle any unhandled exceptions.
        
        Args:
            request: Request instance
            exc: Unhandled exception
            
        Returns:
            JSONResponse: Error response
        """
        error_response = {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "details": {
                    "type": exc.__class__.__name__
                }
            }
        }
        
        logger.error(
            f"Unhandled error: {exc}",
            extra={
                "path": request.url.path,
                "error_type": exc.__class__.__name__
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        ) 