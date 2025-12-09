"""Configuration for Runner Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Runner Service configuration."""

    # Redis for job tracking
    redis_url: str = "redis://redis:6379"

    # Workspace Service
    workspace_service_url: str = "http://workspace-service:8001"

    # Google Cloud configuration
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"

    # Runner images
    node_runner_image: str = "gcr.io/{project}/cahoots-runner-node:20"
    python_runner_image: str = "gcr.io/{project}/cahoots-runner-python:3.11"

    # Job configuration
    default_timeout_seconds: int = 300  # 5 minutes
    max_timeout_seconds: int = 600  # 10 minutes
    sidecar_startup_seconds: int = 30

    # Service authentication
    service_auth_token: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "RUNNER_"


settings = Settings()
