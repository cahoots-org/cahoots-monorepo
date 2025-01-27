"""Team models."""
from datetime import datetime
import uuid
from typing import List
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, UUID, JSON
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from .db_models import Base

class Team(Base):
    """Team model."""
    
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Team {self.name} ({self.id})>"

class TeamMember(Base):
    """Team member model with role."""
    
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role = Column(String, nullable=False)  # tech_lead, developer, designer, qa, etc.
    permissions = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User")

    def __repr__(self) -> str:
        """String representation."""
        return f"<TeamMember {self.user_id} -> {self.team_id} ({self.role})>"

    @property
    def model_serializer(self):
        """Custom serialization."""
        return {
            "id": str,
            "team_id": str,
            "user_id": str,
            "created_at": lambda dt: dt.isoformat() if dt else None,
            "updated_at": lambda dt: dt.isoformat() if dt else None
        } 