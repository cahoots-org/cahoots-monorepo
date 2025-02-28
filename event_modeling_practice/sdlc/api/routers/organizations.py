from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

router = APIRouter()

class OrganizationCreate(BaseModel):
    name: str
    description: str

class OrganizationUpdate(BaseModel):
    name: str
    reason: str

class MemberAdd(BaseModel):
    user_id: UUID
    role: str

class MemberUpdate(BaseModel):
    role: str
    reason: str

@router.post("")
async def create_organization(org: OrganizationCreate, request: Request):
    """Create a new organization"""
    try:
        events = request.state.organization_handler.handle_create_organization(org)
        return {"message": "Organization created", "organization_id": events[0].organization_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{organization_id}")
async def get_organization(organization_id: UUID, request: Request):
    """Get organization details"""
    view = request.state.view_store.get_view(
        organization_id,
        OrganizationDetailsView
    )
    if not view:
        raise HTTPException(status_code=404, detail="Organization not found")
    return view

@router.put("/{organization_id}/name")
async def update_organization_name(
    organization_id: UUID,
    update: OrganizationUpdate,
    request: Request
):
    """Update organization name"""
    try:
        events = request.state.organization_handler.handle_update_name(
            organization_id=organization_id,
            new_name=update.name,
            reason=update.reason
        )
        return {"message": "Organization name updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{organization_id}/members")
async def add_member(
    organization_id: UUID,
    member: MemberAdd,
    request: Request
):
    """Add member to organization"""
    try:
        events = request.state.organization_handler.handle_add_member(
            organization_id=organization_id,
            user_id=member.user_id,
            role=member.role
        )
        return {"message": "Member added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{organization_id}/members/{user_id}")
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    request: Request
):
    """Remove member from organization"""
    try:
        events = request.state.organization_handler.handle_remove_member(
            organization_id=organization_id,
            user_id=user_id
        )
        return {"message": "Member removed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{organization_id}/members/{user_id}/role")
async def update_member_role(
    organization_id: UUID,
    user_id: UUID,
    update: MemberUpdate,
    request: Request
):
    """Update member role"""
    try:
        events = request.state.organization_handler.handle_change_member_role(
            organization_id=organization_id,
            user_id=user_id,
            new_role=update.role,
            reason=update.reason
        )
        return {"message": "Member role updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{organization_id}/members")
async def list_members(organization_id: UUID, request: Request):
    """List organization members"""
    view = request.state.view_store.get_view(
        organization_id,
        OrganizationMembersView
    )
    if not view:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"members": view.members}

@router.get("/{organization_id}/audit-log")
async def get_audit_log(organization_id: UUID, request: Request):
    """Get organization audit log"""
    view = request.state.view_store.get_view(
        organization_id,
        OrganizationAuditLogView
    )
    if not view:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"entries": view.entries} 