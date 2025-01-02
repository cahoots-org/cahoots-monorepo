# src/models/story.py
from pydantic import BaseModel
from typing import List, Optional
from .task import Task

class Story(BaseModel):
    id: str
    title: str
    description: str
    tasks: List[Task] = []
    status: str = "backlog"
    assigned_to: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tasks": [task.to_dict() for task in self.tasks],
            "status": self.status,
            "assigned_to": self.assigned_to
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Story':
        return cls(**data)