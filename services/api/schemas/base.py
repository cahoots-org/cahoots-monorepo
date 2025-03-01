"""Base schemas for API responses and error handling."""
from typing import TypeVar, Generic, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
from enum import Enum

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error categories."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    INFRASTRUCTURE = "infrastructure"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    category: ErrorCategory = Field(..., description="Error category")
    severity: ErrorSeverity = Field(..., description="Error severity")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

DataT = TypeVar("DataT")

class APIResponse(GenericModel, Generic[DataT]):
    """Standard API response format."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[DataT] = Field(None, description="Response data")
    error: Optional[ErrorDetail] = Field(None, description="Error details if request failed")
    meta: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadata about the response (pagination, etc.)"
    )

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page") 