"""Subscription models."""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db_models import Base

class Subscription(Base):
    """Subscription model."""
    
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    tier = Column(String, nullable=False)
    status = Column(String, nullable=False, default='active')
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime)
    price = Column(Float, nullable=False)
    billing_cycle = Column(String, nullable=False)  # monthly, yearly
    auto_renew = Column(Boolean, default=True)
    subscription_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Subscription {self.tier} for {self.organization_id}>" 