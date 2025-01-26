"""Event models for the system."""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLAEnum, Integer, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from .base import Base
from ..types import EventStatus

class EventModel(Base):
    """SQLAlchemy event model."""
    __tablename__ = 'events'

    id = Column(String, primary_key=True, doc="Unique event identifier")
    project_id = Column(String, nullable=False, index=True, doc="Project identifier")
    type = Column(String, nullable=False, doc="Event type")
    status = Column(SQLAEnum(EventStatus), default=EventStatus.PENDING, doc="Event status")
    data = Column(JSON, nullable=True, doc="Event data payload")
    created_at = Column(DateTime, default=datetime.utcnow, doc="Event creation timestamp")
    updated_at = Column(DateTime, nullable=True, doc="Event last update timestamp")
    error = Column(String, nullable=True, doc="Error message if event failed")
    retry_count = Column(Integer, default=0, doc="Retry count")
    priority = Column(Integer, default=0, doc="Priority")

    def dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'type': self.type,
            'status': self.status,
            'data': self.data,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'error': self.error,
            'retry_count': self.retry_count,
            'priority': self.priority
        }

class Event(BaseModel):
    """Event model."""
    id: str
    project_id: str
    type: str
    status: EventStatus = EventStatus.PENDING
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    priority: int = 0
    created_at: datetime = None
    updated_at: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    @classmethod
    def from_orm(cls, db_model: EventModel) -> "Event":
        """Create from database model."""
        return cls(**db_model.dict())

    def to_orm(self) -> EventModel:
        """Convert to database model."""
        return EventModel(**self.dict())

class VersionVector(BaseModel):
    """Version vector for tracking causal ordering."""
    agent_versions: Dict[str, int] = Field(default_factory=lambda: {"master": 0})

class ContextEventModel(Base):
    """SQLAlchemy model for context events."""
    __tablename__ = 'context_events'

    id = Column(String, primary_key=True, doc="Unique event identifier")
    project_id = Column(String, ForeignKey('projects.id'), nullable=False, index=True, doc="Project identifier")
    event_type = Column(String, nullable=False, doc="Type of context event (code_change, architectural_decision, standard_update)")
    event_data = Column(JSON, nullable=False, doc="Event data payload")
    timestamp = Column(DateTime, default=datetime.utcnow, doc="Event timestamp")
    version = Column(Integer, default=1, doc="Event version")
    version_vector = Column(JSON, nullable=False, default={"master": 0}, doc="Version vector for causal ordering")

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'timestamp': self.timestamp,
            'version': self.version,
            'version_vector': self.version_vector
        }

class ContextEvent(BaseModel):
    """Pydantic model for context events."""
    id: str
    project_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    version_vector: VersionVector = Field(default_factory=VersionVector)

    @classmethod
    def from_orm(cls, db_model: ContextEventModel) -> "ContextEvent":
        """Create from database model."""
        return cls(
            id=db_model.id,
            project_id=db_model.project_id,
            event_type=db_model.event_type,
            event_data=db_model.event_data,
            timestamp=db_model.timestamp,
            version=db_model.version,
            version_vector=VersionVector(agent_versions=db_model.version_vector)
        )

    def to_orm(self) -> ContextEventModel:
        """Convert to database model."""
        return ContextEventModel(
            id=self.id,
            project_id=self.project_id,
            event_type=self.event_type,
            event_data=self.event_data,
            timestamp=self.timestamp,
            version=self.version,
            version_vector=self.version_vector.agent_versions
        ) 