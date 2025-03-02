"""Agent API schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentDeployment(BaseModel):
    """Agent deployment request/response model."""

    agent_type: str = Field(..., description="Type of agent to deploy")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Agent-specific configuration"
    )
    status: Optional[str] = Field(None, description="Deployment status")
    replicas: Optional[int] = Field(1, description="Number of replicas to deploy")
    resources: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Resource requirements"
    )

    model_config = ConfigDict(from_attributes=True)


class AgentScaleRequest(BaseModel):
    """Agent scaling request model."""

    replicas: int = Field(..., ge=0, description="Number of replicas to scale to")

    model_config = ConfigDict(from_attributes=True)
