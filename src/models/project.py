# src/models/project.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional
import uuid
from .story import Story

class Project(BaseModel):
    """Project model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "AI Chat Bot",
                "description": "An AI-powered chat bot for customer service"
            }
        },
        str_min_length=1,
        str_max_length=100
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    stories: List[Story] = []
    github_url: Optional[str] = None
    
    @field_validator('name', 'description')
    def validate_string_length(cls, v: str) -> str:
        if len(v) < 1:
            raise ValueError("Field must not be empty")
        if len(v) > 100:
            raise ValueError("Field must not exceed 100 characters")
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Create from dictionary."""
        return cls(**data)