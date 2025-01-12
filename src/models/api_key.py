"""API key model."""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from src.database.database import Base

class APIKey(Base):
    """API key model."""
    __tablename__ = "api_keys"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    hashed_key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Foreign keys
    organization_id = Column(PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")
    
    def is_expired(self) -> bool:
        """Check if API key is expired.
        
        Returns:
            bool: True if expired, False otherwise
        """
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at 