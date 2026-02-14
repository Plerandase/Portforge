from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.team import Team, TeamMember
from app.schemas.team import TeamResponse, TeamMemberResponse, TeamDetailResponse
from app.core.database import get_db

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team_detail(
    team_id: int,
    db: AsyncSession = Depends(get_db)
):
    """팀 상세 정보 조회 (다른 서비스에서 호출)"""
    # 팀 기본 정보 조회
    team_query = select(Team).where(Team.team_id == team_id)
    result = await db.execute(team_query)
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # 팀원 목록 조회
    members_query = select(TeamMember).where(TeamMember.team_id == team_id)
    members_result = await db.execute(members_query)
    members = members_result.scalars().all()
    
    return TeamDetailResponse(
        team_id=team.team_id,
        project_id=team.project_id,
        name=team.name,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=[
            TeamMemberResponse(
                team_id=member.team_id,
                user_id=member.user_id,
                role=member.role,
                position_type=member.position_type,
                created_at=member.created_at,
                updated_at=member.updated_at
            ) for member in members
        ]
    )

@router.get("/{team_id}/basic", response_model=TeamResponse)
async def get_team_basic(
    team_id: int,
    db: AsyncSession = Depends(get_db)
):
    """팀 기본 정보만 조회 (가벼운 조회용)"""
    query = select(Team).where(Team.team_id == team_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    return TeamResponse(
        team_id=team.team_id,
        project_id=team.project_id,
        name=team.name,
        created_at=team.created_at
    )

@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def get_team_members(
    team_id: int,
    db: AsyncSession = Depends(get_db)
):
    """팀원 목록 조회"""
    query = select(TeamMember).where(TeamMember.team_id == team_id)
    result = await db.execute(query)
    members = result.scalars().all()
    
    return [
        TeamMemberResponse(
            team_id=member.team_id,
            user_id=member.user_id,
            role=member.role,
            position_type=member.position_type,
            created_at=member.created_at,
            updated_at=member.updated_at
        ) for member in members
    ]

@router.get("/project/{project_id}", response_model=TeamResponse)
async def get_team_by_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트 ID로 팀 조회"""
    query = select(Team).where(Team.project_id == project_id)
    result = await db.execute(query)
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found for this project"
        )
    
    return TeamResponse(
        team_id=team.team_id,
        project_id=team.project_id,
        name=team.name,
        created_at=team.created_at
    )

@router.post("/batch", response_model=List[TeamResponse])
async def get_teams_batch(
    team_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """여러 팀 정보 일괄 조회"""
    query = select(Team).where(Team.team_id.in_(team_ids))
    result = await db.execute(query)
    teams = result.scalars().all()
    
    return [
        TeamResponse(
            team_id=team.team_id,
            project_id=team.project_id,
            name=team.name,
            created_at=team.created_at
        ) for team in teams
    ]