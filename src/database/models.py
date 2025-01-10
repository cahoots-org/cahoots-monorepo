"""Database models."""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, String, JSON, Boolean, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from .database import Base

class Organization(Base):
    """Organization model."""
    
    __tablename__ = "organizations"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, nullable=False, default="free")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")
    usage_records = relationship("UsageRecord", back_populates="organization")

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
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(String, nullable=False)
    stripe_invoice_id = Column(String, unique=True)
    billing_reason = Column(String)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice(id={self.id}, organization_id={self.organization_id}, amount={self.amount})>"

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