"""Event models for the system."""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLAEnum, Integer, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from uuid import UUID as PyUUID, uuid4

from .base import Base
from ..types import EventStatus, EventPriority

class Base(DeclarativeBase):
    """Base class for all models."""
    pass

class EventModel(Base):
    """SQLAlchemy model for events."""
    __tablename__ = 'events'

    id = Column(UUID, primary_key=True, default=uuid4)
    project_id = Column(UUID, nullable=False)
    type = Column(String, nullable=False)
    status = Column(SQLAEnum(EventStatus), nullable=False, default=EventStatus.PENDING)
    retry_count = Column(Integer, nullable=False, default=0)
    priority = Column(SQLAEnum(EventPriority), nullable=False, default=EventPriority.LOW)
    data = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            'retry_count': self.retry_count,
            'priority': self.priority
        }

class Event(BaseModel):
    """Pydantic model for events."""
    id: PyUUID
    project_id: PyUUID
    type: str
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    priority: EventPriority = EventPriority.LOW
    data: Dict[str, Any]
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, db_model: EventModel) -> "Event":
        return cls(
            id=db_model.id,
            project_id=db_model.project_id,
            type=db_model.type,
            status=db_model.status,
            retry_count=db_model.retry_count,
            priority=db_model.priority,
            data=db_model.data,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )

    def to_orm(self) -> EventModel:
        """Convert to an ORM object."""
        return EventModel(**self.model_dump())

class VersionVector(BaseModel):
    """Version vector for tracking causal ordering."""
    agent_versions: Dict[str, int] = Field(default_factory=lambda: {"master": 0})

    @classmethod
    def new(cls) -> "VersionVector":
        """Create a new version vector with default values."""
        return cls(agent_versions={"master": 0})

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
    """Event model for context changes."""
    id: str = Field(description="Unique identifier for the event")
    project_id: str = Field(description="Project ID this event belongs to")
    event_type: str = Field(description="Type of context event")
    event_data: Dict = Field(description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    version: int = Field(default=1, description="Event version")
    version_vector: VersionVector = Field(default_factory=VersionVector.new, description="Version vector for event")

    # Class-level attributes for SQLAlchemy filtering
    id = None
    project_id = None

    model_config = ConfigDict(from_attributes=True)

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