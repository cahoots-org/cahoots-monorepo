"""Base database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

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
    subscription_tier = Column(String, default="free")
    subscription_status = Column(String, default="active")
    subscription_id = Column(String)
    subscription_item_id = Column(String)
    customer_id = Column(String)
    default_payment_method_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("UserRole", back_populates="organization", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship(
        "OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )
    usage_records = relationship(
        "UsageRecord", back_populates="organization", cascade="all, delete-orphan"
    )
    invoices = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship(
        "Subscription", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Organization {self.name} ({self.id})>"


class OrganizationInvitation(Base):
    """Organization invitation model."""

    __tablename__ = "organization_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
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


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    agent_config = Column(JSON, nullable=False, default=dict)
    resource_limits = Column(JSON, nullable=False, default=dict)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    team = relationship("Team", back_populates="projects")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Project {self.name} ({self.id})>"


class Team(Base):
    """Team model."""

    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
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
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
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


class TeamConfiguration(Base):
    """Team configuration model."""

    __tablename__ = "team_configurations"

    project_id = Column(String, primary_key=True)
    config = Column(JSON, nullable=False)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    changes = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    error = Column(String, nullable=True)
    audit_metadata = Column(JSON, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AuditLog {self.action} on {self.resource_type} ({self.id})>"


class Subscription(Base):
    """Subscription model."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    tier = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime)
    price = Column(Integer, nullable=False)  # Price in cents
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


class UsageRecord(Base):
    """Usage record model."""

    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    metric = Column(String, nullable=False)  # Type of usage being tracked
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    usage_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="usage_records")

    def __repr__(self) -> str:
        """String representation."""
        return f"<UsageRecord {self.metric}: {self.quantity} for {self.organization_id}>"


class Invoice(Base):
    """Invoice model."""

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    amount_due = Column(Integer, nullable=False)  # Amount in cents
    amount_paid = Column(Integer, nullable=False, default=0)  # Amount in cents
    status = Column(String, nullable=False)  # draft, open, paid, void, uncollectible
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    hosted_invoice_url = Column(String)
    pdf_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="invoices")
    subscription = relationship("Subscription")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Invoice {self.id} for {self.organization_id}>"
