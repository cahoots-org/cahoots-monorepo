"""API key model."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from ..utils.infrastructure.database.client import Base

class APIKey(Base):
    """API key model."""
    __tablename__ = 'api_keys'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    organization_id = Column(String, ForeignKey('organizations.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    def __repr__(self):
        """String representation."""
        return f"<APIKey {self.name}>"

    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at 