from dataclasses import dataclass
from uuid import UUID

from ..commands import Command


@dataclass
class CreateTeam(Command):
    organization_id: UUID
    name: str
    description: str
    created_by: UUID


@dataclass
class AddTeamMember(Command):
    team_id: UUID
    member_id: UUID
    role: str
    added_by: UUID


@dataclass
class UpdateTeamMemberRole(Command):
    team_id: UUID
    member_id: UUID
    new_role: str
    reason: str
    updated_by: UUID


@dataclass
class RemoveTeamMember(Command):
    team_id: UUID
    member_id: UUID
    removed_by: UUID


@dataclass
class TransferTeamLeadership(Command):
    team_id: UUID
    new_lead_id: UUID
    transferred_by: UUID


@dataclass
class ArchiveTeam(Command):
    team_id: UUID
    reason: str
    archived_by: UUID
