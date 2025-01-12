"""Database models."""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, String, JSON, Boolean, Integer, Numeric, Table
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from .database import Base
from src.models.api_key import APIKey
from src.models.federation import FederatedIdentityMapping
from src.models.identity_provider import IdentityProvider

user_organizations = Table(
    "user_organizations",
    Base.metadata,
    Column("user_id", PostgresUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("organization_id", PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True),
    Column("role", String, nullable=False, default="member"),
    Column("permissions", JSON, default=lambda: []),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

class Organization(Base):
    """Organization model."""
    
    __tablename__ = "organizations"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    description = Column(String)
    api_key = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, nullable=False, default="free")
    customer_id = Column(String, unique=True)
    subscription_status = Column(String)
    subscription_id = Column(String, unique=True)
    subscription_item_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")
    usage_records = relationship("UsageRecord", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")
    users = relationship("User", secondary="user_organizations", back_populates="organizations")

class Project(Base):
    """Project model."""
    
    __tablename__ = "projects"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    organization_id = Column(PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    context_events = relationship("ContextEvent", back_populates="project")

class ContextEvent(Base):
    """Context event model."""
    
    __tablename__ = "context_events"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    version_vector = Column(JSON, nullable=False, default=lambda: {"master": 0})

    # Relationships
    project = relationship("Project", back_populates="context_events")

    def __repr__(self):
        return f"<ContextEvent(id={self.id}, project_id={self.project_id}, type={self.event_type})>"

class Invoice(Base):
    """Invoice model."""
    
    __tablename__ = "invoices"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String, nullable=False)
    subscription_id = Column(String, nullable=False)
    amount_due = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice(id={self.id}, organization_id={self.organization_id}, amount_due={self.amount_due})>"

class UsageRecord(Base):
    """Usage record model."""
    
    __tablename__ = "usage_records"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    metric = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    usage_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    organization = relationship("Organization", back_populates="usage_records")

    def __repr__(self):
        return f"<UsageRecord(id={self.id}, organization_id={self.organization_id}, metric={self.metric}, quantity={self.quantity})>"

class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    preferences = Column(JSON, default=lambda: {
        "notification_settings": {
            "email": True,
            "in_app": True
        },
        "theme": "light"
    })

    # Relationships
    api_keys = relationship("APIKey", back_populates="user")
    organizations = relationship("Organization", secondary="user_organizations", back_populates="users")
    federated_identities = relationship("FederatedIdentityMapping", back_populates="user")