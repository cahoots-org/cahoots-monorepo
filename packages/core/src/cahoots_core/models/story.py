# src/models/story.py
from typing import Optional
from pydantic import BaseModel, ConfigDict

class Story(BaseModel):
    """Story model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "story-1",
                "title": "User Registration",
                "description": "Implement user registration with email verification",
                "priority": 1,
                "status": "open"
            }
        }
    )
    
    id: str
    title: str
    description: str
    priority: int
    status: str = "open"