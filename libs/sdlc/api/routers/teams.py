from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from ...domain.team.views import TeamView

router = APIRouter()

class TeamCreate(BaseModel):
    organization_id: UUID
    name: str
    description: str

class TeamMemberAdd(BaseModel):
    member_id: UUID
    role: str

class TeamMemberUpdate(BaseModel):
    new_role: str
    reason: str

class TeamArchive(BaseModel):
    reason: str

@router.post("")
async def create_team(team: TeamCreate, request: Request):
    """Create a new team"""
    try:
        events = request.state.organization_handler.handle_create_team(team)
        return {"message": "Team created", "team_id": events[0].team_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{team_id}")
async def get_team(team_id: UUID, request: Request):
    """Get team details"""
    view = request.state.view_store.get_view(
        team_id,
        TeamView
    )
    if not view:
        raise HTTPException(status_code=404, detail="Team not found")
    return view

@router.post("/{team_id}/members")
async def add_team_member(
    team_id: UUID,
    member: TeamMemberAdd,
    request: Request
):
    """Add member to team"""
    try:
        events = request.state.organization_handler.handle_add_team_member(
            team_id=team_id,
            member_id=member.member_id,
            role=member.role
        )
        return {"message": "Member added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: UUID,
    member_id: UUID,
    request: Request
):
    """Remove member from team"""
    try:
        events = request.state.organization_handler.handle_remove_team_member(
            team_id=team_id,
            member_id=member_id
        )
        return {"message": "Member removed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{team_id}/members/{member_id}/role")
async def update_team_member_role(
    team_id: UUID,
    member_id: UUID,
    update: TeamMemberUpdate,
    request: Request
):
    """Update team member role"""
    try:
        events = request.state.organization_handler.handle_update_team_member_role(
            team_id=team_id,
            member_id=member_id,
            new_role=update.new_role,
            reason=update.reason
        )
        return {"message": "Member role updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{team_id}/transfer-leadership/{new_lead_id}")
async def transfer_team_leadership(
    team_id: UUID,
    new_lead_id: UUID,
    request: Request
):
    """Transfer team leadership"""
    try:
        events = request.state.organization_handler.handle_transfer_team_leadership(
            team_id=team_id,
            new_lead_id=new_lead_id
        )
        return {"message": "Leadership transferred"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{team_id}/archive")
async def archive_team(
    team_id: UUID,
    archive: TeamArchive,
    request: Request
):
    """Archive team"""
    try:
        events = request.state.organization_handler.handle_archive_team(
            team_id=team_id,
            reason=archive.reason
        )
        return {"message": "Team archived"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{team_id}/members")
async def list_team_members(team_id: UUID, request: Request):
    """List team members"""
    view = request.state.view_store.get_view(
        team_id,
        TeamView
    )
    if not view:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"members": view.members} 