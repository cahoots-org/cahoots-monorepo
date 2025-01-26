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

class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    ssl: bool = Field(default=False, description="Use SSL for Redis connection")
    pool_size: int = Field(default=10, description="Redis connection pool size")
    timeout: int = Field(default=5, description="Redis connection timeout")

class ServiceConfig(BaseModel):
    """Base configuration with common fields."""
    
    # Service configuration
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    api_key: Optional[str] = Field(default=None, description="API key for service authentication")
    workspace_dir: str = Field(default_factory=lambda: tempfile.gettempdir(), description="Workspace directory for service")
    repo_name: Optional[str] = Field(default=None, description="Repository name for service")
    
    # Redis configuration
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    
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

class SecurityConfig(BaseModel):
    """Security configuration."""
    
    # JWT configuration
    jwt_secret_key: str = Field(..., description="Secret key for JWT tokens")
    jwt_algorithm: str = Field(default="HS256", description="Algorithm for JWT tokens")
    jwt_expiration: int = Field(default=3600, description="JWT token expiration in seconds")
    
    # Authentication configuration
    token_expire_minutes: int = Field(default=30, description="Token expiration time in minutes")
    min_password_length: int = Field(default=8, description="Minimum password length")
    password_reset_expire_minutes: int = Field(default=15, description="Password reset token expiration in minutes")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=60, description="Number of requests allowed per minute")
    rate_limit_burst: int = Field(default=10, description="Maximum burst size for rate limiting")
    
    # API Security
    allowed_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    api_key_prefix: str = Field(default="sk_", description="Prefix for API keys")
    
    @field_validator("min_password_length")
    def validate_min_password_length(cls, v: int) -> int:
        """Validate minimum password length is reasonable."""
        if v < 8:
            raise ConfigurationError("Minimum password length must be at least 8 characters")
        return v
        
    @field_validator("token_expire_minutes")
    def validate_token_expire_minutes(cls, v: int) -> int:
        """Validate token expiration time is positive."""
        if v <= 0:
            raise ConfigurationError("Token expiration time must be positive")
        return v 

@lru_cache()
def get_settings() -> ServiceConfig:
    """Get cached application settings.
    
    Returns:
        ServiceConfig: Application settings
    """
    return ServiceConfig(
        name="cahoots-service",
        url="http://localhost:8000",
        timeout=30,
        retry_attempts=3,
        retry_delay=1
    ) 