"""Organization invitation model."""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, UUID
from sqlalchemy.orm import relationship

from .db_models import Base

class OrganizationInvitation(Base):
    """Organization invitation model."""
    
    __tablename__ = "organization_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True)
    is_accepted = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="invitations")

    def __repr__(self) -> str:
        """String representation."""
        return f"<OrganizationInvitation {self.email} -> {self.organization_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired."""
        return datetime.utcnow() > self.expires_at 