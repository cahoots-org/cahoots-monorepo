# src/models/project.py
from pydantic import BaseModel
from typing import List
from .story import Story

class Project(BaseModel):
    id: str
    name: str
    description: str
    stories: List[Story] = []
    github_url: str = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stories": [story.to_dict() for story in self.stories],
            "github_url": self.github_url
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        return cls(**data)