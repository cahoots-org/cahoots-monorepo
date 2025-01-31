"""Utility decorators."""
from functools import wraps
from typing import Any, Callable, Optional
from cahoots_core.exceptions import InfrastructureError
from ...utils.metrics import TRELLO_ERROR_COUNTER

def service_error_handler(
    service_name: str,
    metric_counter: Optional[Any] = None,
    method: Optional[str] = None,
    endpoint: Optional[str] = None
):
    """Handle common service error patterns.
    
    Args:
        service_name: Name of the service (e.g. "Trello")
        metric_counter: Counter metric to increment on errors
        method: HTTP method for metrics (e.g. "GET", "POST")
        endpoint: API endpoint for metrics
        
    Returns:
        Decorator function that wraps service methods
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation = func.__name__
            try:
                return await func(*args, **kwargs)
            except InfrastructureError:
                # Re-raise infrastructure errors without wrapping
                raise
            except Exception as e:
                if metric_counter is not None:
                    metric_counter.labels(
                        method=method or "UNKNOWN",
                        endpoint=endpoint or "UNKNOWN",
                        status_code="500"
                    ).inc()
                raise InfrastructureError(
                    message=str(e),
                    service=service_name,
                    operation=operation
                )
        return wrapper
    return decorator 