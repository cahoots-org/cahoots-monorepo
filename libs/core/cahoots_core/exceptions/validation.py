"""Validation exceptions for the Cahoots system."""

from typing import Any, Dict, Optional, Union

from .base import CahootsError, ErrorCategory, ErrorSeverity


class ValidationError(CahootsError):
    """Base class for validation-related errors."""

    def __init__(
        self, message: str, *, field: Optional[str] = None, value: Optional[Any] = None, **kwargs
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: Value that failed validation
            **kwargs: Additional arguments passed to CahootsError
        """
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            details={"field": field, "value": value, **(kwargs.pop("details", {}) or {})},
            **kwargs,
        )


class DataValidationError(ValidationError):
    """Data validation error."""

    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            message,
            code="DATA_VALIDATION_ERROR",
            severity=ErrorSeverity.WARNING,
            details={"validation_errors": errors, **(kwargs.pop("details", {}) or {})},
            **kwargs,
        )


class SchemaValidationError(ValidationError):
    """Schema validation error."""

    def __init__(
        self,
        message: str,
        schema_name: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(
            message,
            code="SCHEMA_VALIDATION_ERROR",
            severity=ErrorSeverity.WARNING,
            details={
                "schema_name": schema_name,
                "validation_errors": errors,
                **(kwargs.pop("details", {}) or {}),
            },
            **kwargs,
        )


class TypeValidationError(ValidationError):
    """Type validation error."""

    def __init__(
        self,
        message: str,
        expected_type: Optional[Union[str, type]] = None,
        actual_type: Optional[Union[str, type]] = None,
        **kwargs,
    ):
        super().__init__(
            message,
            code="TYPE_VALIDATION_ERROR",
            severity=ErrorSeverity.WARNING,
            details={
                "expected_type": str(expected_type),
                "actual_type": str(actual_type),
                **(kwargs.pop("details", {}) or {}),
            },
            **kwargs,
        )


class FormatValidationError(ValidationError):
    """Format validation error."""

    def __init__(
        self,
        message: str,
        format_name: Optional[str] = None,
        pattern: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message,
            code="FORMAT_VALIDATION_ERROR",
            severity=ErrorSeverity.WARNING,
            details={
                "format": format_name,
                "pattern": pattern,
                **(kwargs.pop("details", {}) or {}),
            },
            **kwargs,
        )
