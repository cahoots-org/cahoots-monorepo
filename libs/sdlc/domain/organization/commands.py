from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from ..commands import Command


@dataclass
class CreateOrganization(Command):
    """Command to create a new organization"""
    name: str
    description: str
    created_by: UUID


@dataclass
class UpdateOrganizationName(Command):
    """Command to update an organization's name"""
    organization_id: UUID
    new_name: str
    reason: str
    updated_by: UUID


@dataclass
class AddOrganizationMember(Command):
    """Command to add a member to an organization"""
    organization_id: UUID
    user_id: UUID
    role: str
    added_by: UUID


@dataclass
class RemoveOrganizationMember(Command):
    """Command to remove a member from an organization"""
    organization_id: UUID
    user_id: UUID
    removed_by: UUID
    reason: Optional[str] = None


@dataclass
class ChangeOrganizationMemberRole(Command):
    """Command to change a member's role"""
    organization_id: UUID
    user_id: UUID
    new_role: str
    reason: str
    changed_by: UUID


@dataclass
class ArchiveOrganization(Command):
    """Command to archive an organization"""
    organization_id: UUID
    reason: str
    archived_by: UUID 