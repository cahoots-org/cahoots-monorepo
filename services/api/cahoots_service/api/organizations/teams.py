"""Team management endpoints."""
from typing import Dict, List, Optional
from uuid import UUID
from cahoots_core.models.project import Project
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from cahoots_core.models.team import Team, TeamMember
from cahoots_core.models.user import User
from cahoots_core.exceptions import ServiceError

from ...schemas.teams import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamMemberAdd,
    TeamMemberUpdate,
    TeamMemberResponse,
    TeamProjectAssignment
)
from ...services.team_service import TeamService
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/organizations/{organization_id}/teams", tags=["teams"])

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    organization_id: UUID,
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TeamResponse:
    """Create a new team in the organization.
    
    Args:
        organization_id: Organization ID
        team_data: Team creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created team details
        
    Raises:
        HTTPException: If team creation fails
    """
    # Check if team name exists in organization
    stmt = select(Team).where(
        Team.organization_id == organization_id,
        Team.name == team_data.name
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team with this name already exists in the organization"
        )
    
    try:
        # Create team
        team = Team(
            organization_id=organization_id,
            name=team_data.name,
            description=team_data.description,
            settings=team_data.settings
        )
        db.add(team)
        
        # Add creator as tech lead
        member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role="tech_lead",
            permissions={"manage_team": True, "manage_projects": True}
        )
        db.add(member)
        
        await db.commit()
        await db.refresh(team)
        
        return await _team_to_response(team, db)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("", response_model=List[TeamResponse])
async def list_teams(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[TeamResponse]:
    """List teams in the organization.
    
    Args:
        organization_id: Organization ID
        db: Database session
        
    Returns:
        List of teams
    """
    stmt = select(Team).where(Team.organization_id == organization_id)
    result = await db.execute(stmt)
    teams = result.scalars().all()
    
    return [await _team_to_response(team, db) for team in teams]

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    organization_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TeamResponse:
    """Get team details.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        db: Database session
        
    Returns:
        Team details
        
    Raises:
        HTTPException: If team not found
    """
    team = await _get_team(organization_id, team_id, db)
    return await _team_to_response(team, db)

@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    organization_id: UUID,
    team_id: UUID,
    team_data: TeamUpdate,
    db: AsyncSession = Depends(get_db)
) -> TeamResponse:
    """Update team details.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        team_data: Team update data
        db: Database session
        
    Returns:
        Updated team details
        
    Raises:
        HTTPException: If update fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    if team_data.name is not None:
        # Check if new name conflicts
        if team_data.name != team.name:
            stmt = select(Team).where(
                Team.organization_id == organization_id,
                Team.name == team_data.name
            )
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Team with this name already exists in the organization"
                )
        team.name = team_data.name
    
    if team_data.description is not None:
        team.description = team_data.description
    
    if team_data.settings is not None:
        team.settings = team_data.settings
    
    try:
        await db.commit()
        await db.refresh(team)
        return await _team_to_response(team, db)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    organization_id: UUID,
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a team.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        db: Database session
        
    Raises:
        HTTPException: If deletion fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    try:
        await db.delete(team)
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    organization_id: UUID,
    team_id: UUID,
    member_data: TeamMemberAdd,
    db: AsyncSession = Depends(get_db)
) -> TeamMemberResponse:
    """Add a member to the team.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        member_data: Member data
        db: Database session
        
    Returns:
        Added member details
        
    Raises:
        HTTPException: If addition fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    # Check if user exists and is in organization
    stmt = select(User).where(User.id == member_data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not any(role.organization_id == str(organization_id) for role in user.organizations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of the organization"
        )
    
    # Check if already in team
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == member_data.user_id
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member"
        )
    
    try:
        member = TeamMember(
            team_id=team_id,
            user_id=member_data.user_id,
            role=member_data.role,
            permissions=member_data.permissions
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        
        return await _member_to_response(member, db)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member(
    organization_id: UUID,
    team_id: UUID,
    user_id: UUID,
    member_data: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db)
) -> TeamMemberResponse:
    """Update team member details.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        user_id: User ID
        member_data: Member update data
        db: Database session
        
    Returns:
        Updated member details
        
    Raises:
        HTTPException: If update fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a team member"
        )
    
    if member_data.role is not None:
        member.role = member_data.role
    
    if member_data.permissions is not None:
        member.permissions = member_data.permissions
    
    try:
        await db.commit()
        await db.refresh(member)
        return await _member_to_response(member, db)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    organization_id: UUID,
    team_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a member from the team.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        user_id: User ID
        db: Database session
        
    Raises:
        HTTPException: If removal fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a team member"
        )
    
    try:
        await db.delete(member)
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{team_id}/projects", status_code=status.HTTP_204_NO_CONTENT)
async def assign_project(
    organization_id: UUID,
    team_id: UUID,
    assignment: TeamProjectAssignment,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Assign a project to the team.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        assignment: Project assignment data
        db: Database session
        
    Raises:
        HTTPException: If assignment fails
    """
    team = await _get_team(organization_id, team_id, db)
    
    # Check if project exists and belongs to organization
    stmt = select(Project).where(
        Project.id == assignment.project_id,
        Project.organization_id == organization_id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in organization"
        )
    
    try:
        project.team_id = team_id
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def _get_team(organization_id: UUID, team_id: UUID, db: AsyncSession) -> Team:
    """Get team by ID and organization ID.
    
    Args:
        organization_id: Organization ID
        team_id: Team ID
        db: Database session
        
    Returns:
        Team instance
        
    Raises:
        HTTPException: If team not found
    """
    stmt = select(Team).where(
        Team.organization_id == organization_id,
        Team.id == team_id
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    return team

async def _team_to_response(team: Team, db: AsyncSession) -> TeamResponse:
    """Convert team model to response schema.
    
    Args:
        team: Team instance
        db: Database session
        
    Returns:
        Team response
    """
    # Get project count
    stmt = select(func.count()).where(Project.team_id == team.id)
    result = await db.execute(stmt)
    project_count = result.scalar_one()
    
    # Get member details
    members = []
    for member in team.members:
        members.append(await _member_to_response(member, db))
    
    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        settings=team.settings,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members,
        project_count=project_count
    )

async def _member_to_response(member: TeamMember, db: AsyncSession) -> TeamMemberResponse:
    """Convert team member model to response schema.
    
    Args:
        member: Team member instance
        db: Database session
        
    Returns:
        Team member response
    """
    stmt = select(User).where(User.id == member.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one()
    
    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        team_id=member.team_id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        permissions=member.permissions,
        created_at=member.created_at,
        updated_at=member.updated_at
    ) 