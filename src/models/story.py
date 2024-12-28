# src/models/story.py
from pydantic import BaseModel
from typing import List
from .task import Task

class Story(BaseModel):
    id: str
    title: str
    description: str
    tasks: List[Task] = []
    status: str = "backlog"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tasks": [task.to_dict() for task in self.tasks],
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Story':
        return cls(**data)