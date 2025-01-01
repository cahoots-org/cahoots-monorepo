"""Validation utilities for data validation and sanitization."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ValidationError, validator
import re
from datetime import datetime
from uuid import UUID

class ValidationResult(BaseModel):
    """Result of a validation operation."""
    is_valid: bool
    errors: List[Dict[str, str]] = []

def validate_uuid(value: str) -> ValidationResult:
    """
    Validate a UUID string.
    
    Args:
        value: String to validate as UUID
        
    Returns:
        ValidationResult with validation status and any errors
    """
    try:
        UUID(value)
        return ValidationResult(is_valid=True)
    except ValueError:
        return ValidationResult(
            is_valid=False,
            errors=[{"field": "uuid", "message": "Invalid UUID format"}]
        )

def validate_datetime(value: str) -> ValidationResult:
    """
    Validate a datetime string.
    
    Args:
        value: String to validate as datetime
        
    Returns:
        ValidationResult with validation status and any errors
    """
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
        return ValidationResult(is_valid=True)
    except (ValueError, TypeError):
        return ValidationResult(
            is_valid=False,
            errors=[{"field": "datetime", "message": "Invalid datetime format"}]
        )

def validate_email(value: str) -> ValidationResult:
    """
    Validate an email address.
    
    Args:
        value: String to validate as email
        
    Returns:
        ValidationResult with validation status and any errors
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_regex, value):
        return ValidationResult(is_valid=True)
    return ValidationResult(
        is_valid=False,
        errors=[{"field": "email", "message": "Invalid email format"}]
    )

def validate_url(value: str) -> ValidationResult:
    """
    Validate a URL.
    
    Args:
        value: String to validate as URL
        
    Returns:
        ValidationResult with validation status and any errors
    """
    url_regex = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)$'
    if re.match(url_regex, value):
        return ValidationResult(is_valid=True)
    return ValidationResult(
        is_valid=False,
        errors=[{"field": "url", "message": "Invalid URL format"}]
    )

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """
    Validate that all required fields are present in a dictionary.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        ValidationResult with validation status and any errors
    """
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return ValidationResult(
            is_valid=False,
            errors=[{
                "field": field,
                "message": "Required field is missing"
            } for field in missing_fields]
        )
    return ValidationResult(is_valid=True)

def validate_field_length(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> ValidationResult:
    """
    Validate the length of a string field.
    
    Args:
        value: String to validate
        field_name: Name of the field being validated
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        
    Returns:
        ValidationResult with validation status and any errors
    """
    if min_length is not None and len(value) < min_length:
        return ValidationResult(
            is_valid=False,
            errors=[{
                "field": field_name,
                "message": f"Field must be at least {min_length} characters long"
            }]
        )
    
    if max_length is not None and len(value) > max_length:
        return ValidationResult(
            is_valid=False,
            errors=[{
                "field": field_name,
                "message": f"Field must be at most {max_length} characters long"
            }]
        )
    
    return ValidationResult(is_valid=True)

def validate_numeric_range(
    value: Union[int, float],
    field_name: str,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None
) -> ValidationResult:
    """
    Validate that a numeric value is within a specified range.
    
    Args:
        value: Number to validate
        field_name: Name of the field being validated
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        ValidationResult with validation status and any errors
    """
    if min_value is not None and value < min_value:
        return ValidationResult(
            is_valid=False,
            errors=[{
                "field": field_name,
                "message": f"Value must be greater than or equal to {min_value}"
            }]
        )
    
    if max_value is not None and value > max_value:
        return ValidationResult(
            is_valid=False,
            errors=[{
                "field": field_name,
                "message": f"Value must be less than or equal to {max_value}"
            }]
        )
    
    return ValidationResult(is_valid=True)

def sanitize_string(value: str) -> str:
    """
    Sanitize a string by removing potentially dangerous characters.
    
    Args:
        value: String to sanitize
        
    Returns:
        Sanitized string
    """
    # Remove control characters and non-printable characters
    value = ''.join(char for char in value if char.isprintable())
    
    # HTML escape special characters
    value = value.replace('&', '&amp;')
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&#x27;')
    
    return value.strip()

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: Dictionary to sanitize
        
    Returns:
        Dictionary with sanitized string values
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized 