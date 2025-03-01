from dataclasses import dataclass
from typing import Dict, List
from uuid import UUID
from ..commands import Command


@dataclass
class ProposeCodeChange(Command):
    project_id: UUID
    files: List[str]
    description: str
    reasoning: str
    proposed_by: UUID


@dataclass
class ReviewCodeChange(Command):
    project_id: UUID
    change_id: UUID
    status: str
    comments: str
    suggested_changes: str
    reviewed_by: UUID


@dataclass
class ImplementCodeChange(Command):
    project_id: UUID
    change_id: UUID
    implemented_by: UUID 