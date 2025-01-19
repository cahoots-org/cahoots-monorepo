"""Federation models."""
from typing import Dict
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db_models import Base
from .identity_provider import IdentityProvider
from .user import User

class FederatedIdentityMapping(Base):
    """Federated identity mapping model."""
    
    __tablename__ = "federated_identity_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('identity_providers.id'), nullable=False)
    external_id = Column(String, nullable=False)
    attributes = Column(JSON, nullable=False)
    mapping_metadata = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="federated_identities")
    provider = relationship("IdentityProvider")

    def __repr__(self) -> str:
        """String representation."""
        return f"<FederatedIdentityMapping {self.external_id}>"

class TrustRelationship(Base):
    """Federation trust relationship model."""
    
    __tablename__ = "trust_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('identity_providers.id'), nullable=False)
    trusted_provider_id = Column(UUID(as_uuid=True), ForeignKey('identity_providers.id'), nullable=False)
    trust_level = Column(String, nullable=False)  # direct, transitive
    relationship_metadata = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    provider = relationship("IdentityProvider", foreign_keys=[provider_id])
    trusted_provider = relationship("IdentityProvider", foreign_keys=[trusted_provider_id])

    def __repr__(self) -> str:
        """String representation."""
        return f"<TrustRelationship {self.provider_id} -> {self.trusted_provider_id}>"

class AttributeMapping(Base):
    """Federation attribute mapping model."""
    
    __tablename__ = "attribute_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('identity_providers.id'), nullable=False)
    source_attribute = Column(String, nullable=False)
    target_attribute = Column(String, nullable=False)
    transform_function = Column(String)  # Optional transformation function name
    is_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    provider = relationship("IdentityProvider")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AttributeMapping {self.source_attribute} -> {self.target_attribute}>" 