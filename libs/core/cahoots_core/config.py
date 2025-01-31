from pydantic_settings import BaseSettings
from pydantic import Field

class Config(BaseSettings):
    """Base configuration class for Cahoots services."""
    
    # Service configuration
    service_name: str = Field(default="cahoots", description="Name of the service")
    service_version: str = Field(default="0.1.0", description="Version of the service")
    
    # Environment configuration
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode flag")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to listen on")
    
    # Redis configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str = Field(default="", description="Redis password")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format (json or text)")
    
    class Config:
        env_file = ".env"
        case_sensitive = False 