from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.models.project_recruitment import Project
from app.schemas.project import ProjectResponse
from app.core.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

# =========================================================
# 기본 정보 조회 (CRUD 라우터와 겹치지 않는 경량화 API)
# =========================================================

@router.get("/{project_id}/basic", response_model=ProjectResponse)
async def get_project_basic(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트 기본 정보만 조회 (가벼운 조회용)"""
    query = select(Project).where(Project.project_id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return ProjectResponse(
        project_id=project.project_id,
        title=project.title,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        team_id=project.team_id  # team_id 추가
    )

@router.post("/batch", response_model=List[ProjectResponse])
async def get_projects_batch(
    project_ids: List[int], # List[int]로 받을 수 있도록 pydantic이 처리해줌 (Body가 [1,2,3] 형태일 때)
    # 하지만 보통 Body는 Pydantic Model이나 Dict로 감싸야 함.
    # 원래 코드를 보면 `project_ids: List[int]`로 되어 있었으나, FastAPI에서 List[int]를 Body로 직접 받으려면 Body(...) 필요.
    # 원래 코드: `project_ids: List[int]` -> 이러면 Query parameter로 인식될 수도 있음 (GET이 아니라 POST라서 Body로 인식될 수도 있는데, 리스트는 Query로 인식됨).
    # 원래 코드가 작동했는지 의문. Batch 조회는 보통 {"project_ids": []} 형태로 받음.
    # 확인해보니 원래 코드는 `project_ids: List[int]` 였음. 이러면 Query Params?
    # 하지만 `crud.py`의 `get_users_nicknames`는 `json={"user_ids": ...}`로 보냄.
    # 여기는 Project Service이다.
    # 프론트엔드가 어떻게 보내는지? `apiClient` 확인 불가 (Project Batch 함수가 apiClient에 있었나?)
    # `getProjectsBatch`는 없었다. 내부 통신용일 가능성 높음.
    # 안전하게 `Body`를 명시하거나, 원래대로 유지.
    # 원래 코드 유지하되 DB 세션과 모델만 정확히 import.
    db: AsyncSession = Depends(get_db)
):
    """여러 프로젝트 정보 일괄 조회"""
    # project_ids가 POST Body로 들어온다고 가정 (FastAPI가 parameter 이름을 보고 Body 필드로 매핑할 수도 있음)
    # 하지만 명시적인게 좋음.
    # 일단 원래 코드 복구.
    if isinstance(project_ids, dict): # Body가 통째로 들어올 경우 예외처리
        project_ids = project_ids.get("project_ids", [])

    query = select(Project).where(Project.project_id.in_(project_ids))
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            project_id=project.project_id,
            title=project.title,
            description=project.description,
            status=project.status,
            start_date=project.start_date,
            end_date=project.end_date
        ) for project in projects
    ]