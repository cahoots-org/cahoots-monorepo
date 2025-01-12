"""Identity provider model."""
from typing import Dict, Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID

from src.database.database import Base

class IdentityProvider(Base):
    """Identity provider model for SSO configurations."""
    
    __tablename__ = "identity_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(String, nullable=False)  # saml, oidc, etc.
    entity_id = Column(String, unique=True, nullable=False)
    provider_metadata = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<IdentityProvider {self.name}>" 