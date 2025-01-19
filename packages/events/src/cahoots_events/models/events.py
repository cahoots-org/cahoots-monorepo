"""Event models for the system."""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLAEnum, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
import json
from uuid import UUID

Base = declarative_base()

class EventStatus(str, Enum):
    """Event status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Event(Base):
    """Base event model."""
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
        
    def model_dump(self):
        """Pydantic v2 compatible model dump method."""
        return self.dict() 

    def model_dump_json(self):
        """Pydantic v2 compatible JSON serialization method."""
        return json.dumps(self.dict(), default=str) 

class ContextEvent(Base):
    """Event model for context changes."""
    __tablename__ = 'context_events'

    id = Column(String, primary_key=True, doc="Unique event identifier")
    project_id = Column(String, ForeignKey('projects.id'), nullable=False, index=True, doc="Project identifier")
    event_type = Column(String, nullable=False, doc="Type of context event (code_change, architectural_decision, standard_update)")
    event_data = Column(JSON, nullable=False, doc="Event data payload")
    timestamp = Column(DateTime, default=datetime.utcnow, doc="Event timestamp")
    version = Column(Integer, default=1, doc="Event version")
    
    def dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'timestamp': self.timestamp,
            'version': self.version
        }
        
    def model_dump(self):
        """Pydantic v2 compatible model dump method."""
        return self.dict()

    def model_dump_json(self):
        """Pydantic v2 compatible JSON serialization method."""
        return json.dumps(self.dict(), default=str) 