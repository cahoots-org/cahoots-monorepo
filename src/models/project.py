# src/models/project.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .story import Story

class Project(BaseModel):
    """Project model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "project-123",
                "name": "AI Chat Bot",
                "description": "An AI-powered chat bot for customer service",
                "stories": [],
                "github_url": "https://github.com/org/repo"
            }
        }
    )
    
    id: str
    name: str
    description: str
    stories: List[Story] = []
    github_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Create from dictionary."""
        return cls(**data)