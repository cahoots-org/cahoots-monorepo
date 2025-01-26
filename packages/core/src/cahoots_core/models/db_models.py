"""Base database models."""
from datetime import datetime
import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

Base = declarative_base()

class Organization(Base):
    """Organization model."""
    
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    description = Column(String)
    api_key = Column(String, unique=True, nullable=False)
    api_rate_limit = Column(Integer, default=1000)
    subscription_tier = Column(String, default='free')
    subscription_status = Column(String, default='active')
    subscription_id = Column(String)
    subscription_item_id = Column(String)
    customer_id = Column(String)
    default_payment_method_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("UserRole", back_populates="organization", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="organization", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Organization {self.name} ({self.id})>"

class TeamConfiguration(Base):
    """Team configuration model."""
    
    __tablename__ = "team_configurations"

    project_id = Column(String, primary_key=True)
    config = Column(JSON, nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False) 