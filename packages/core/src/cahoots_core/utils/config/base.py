"""Configuration management and validation module."""
from typing import Dict, List, Optional, Any
from pydantic import (
    BaseModel, 
    field_validator,
    model_validator,
    ConfigDict,
    SecretStr,
    Field
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import tempfile
import os
import yaml
import logging
from dataclasses import dataclass
from pathlib import Path

from ...utils.errors.exceptions import ConfigurationError

class ServiceConfig(BaseModel):
    """Base configuration for services with common fields."""
    
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    api_key: Optional[str] = Field(default=None, description="API key for service authentication")
    
    @field_validator("timeout")
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ConfigurationError("Timeout must be positive")
        return v
        
    @field_validator("retry_attempts")
    def validate_retry_attempts(cls, v: int) -> int:
        """Validate retry attempts is non-negative."""
        if v < 0:
            raise ConfigurationError("Retry attempts must be non-negative")
        return v
        
    @field_validator("retry_delay") 
    def validate_retry_delay(cls, v: int) -> int:
        """Validate retry delay is positive."""
        if v <= 0:
            raise ConfigurationError("Retry delay must be positive")
        return v 