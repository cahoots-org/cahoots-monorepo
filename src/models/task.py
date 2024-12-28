# src/models/task.py
from pydantic import BaseModel

class Task(BaseModel):
    id: str
    title: str
    description: str
    requires_ux: bool = False
    status: str = "pending"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requires_ux": self.requires_ux,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        return cls(**data)