from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.project_recruitment import Project, Application
from app.schemas.project import ProjectResponse, ApplicationResponse
from app.core.database import get_db
from app.utils.msa_client import msa_client, enrich_data_with_user_info

router = APIRouter(prefix="/enriched", tags=["enriched-data"])

@router.get("/projects/{project_id}/applications-with-users")
async def get_project_applications_with_user_info(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트 지원서 목록을 사용자 정보와 함께 조회 (MSA 통신 예시)"""
    
    # 1. 프로젝트 지원서 목록 조회 (자신의 DB)
    query = select(Application).where(Application.project_id == project_id)
    result = await db.execute(query)
    applications = result.scalars().all()
    
    if not applications:
        return []
    
    # 2. 지원서 데이터를 딕셔너리로 변환
    applications_data = [
        {
            "application_id": app.application_id,
            "project_id": app.project_id,
            "user_id": app.user_id,
            "position_type": app.position_type.value,
            "status": app.status.value,
            "created_at": app.created_at.isoformat()
        } for app in applications
    ]
    
    # 3. Auth Service에서 사용자 정보 조회 및 데이터 보강
    enriched_applications = await enrich_data_with_user_info(applications_data)
    
    # 4. AI Service에서 테스트 결과 조회 및 추가
    for app_data in enriched_applications:
        test_result = await msa_client.get_test_result_by_application(app_data["application_id"])
        if test_result:
            app_data["test_result"] = {
                "score": test_result.get("score"),
                "feedback": test_result.get("feedback"),
                "created_at": test_result.get("created_at")
            }
    
    return enriched_applications

@router.get("/projects/with-leader-info")
async def get_projects_with_leader_info(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트 목록을 팀장 정보와 함께 조회"""
    
    # 1. 프로젝트 목록 조회
    query = select(Project).offset(offset).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    if not projects:
        return []
    
    # 2. 프로젝트 데이터를 딕셔너리로 변환
    projects_data = [
        {
            "project_id": project.project_id,
            "user_id": project.user_id,  # 팀장 ID
            "title": project.title,
            "description": project.description,
            "status": project.status.value,
            "start_date": project.start_date.isoformat(),
            "end_date": project.end_date.isoformat(),
            "created_at": project.created_at.isoformat()
        } for project in projects
    ]
    
    # 3. Auth Service에서 팀장 정보 조회 및 데이터 보강
    enriched_projects = await enrich_data_with_user_info(projects_data)
    
    return enriched_projects

@router.get("/applications/{application_id}/full-detail")
async def get_application_full_detail(
    application_id: int,
    db: AsyncSession = Depends(get_db)
):
    """지원서 상세 정보를 모든 관련 데이터와 함께 조회"""
    
    # 1. 지원서 기본 정보 조회
    query = select(Application).where(Application.application_id == application_id)
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # 2. 기본 지원서 데이터
    app_data = {
        "application_id": application.application_id,
        "project_id": application.project_id,
        "user_id": application.user_id,
        "position_type": application.position_type.value,
        "status": application.status.value,
        "message": application.message,
        "created_at": application.created_at.isoformat()
    }
    
    # 3. 사용자 정보 조회 (Auth Service)
    user_info = await msa_client.get_user_detail(application.user_id)
    if user_info:
        app_data["user_info"] = user_info
    
    # 4. 프로젝트 정보 조회 (자신의 서비스이지만 API 호출 예시)
    project_info = await msa_client.get_project_detail(application.project_id)
    if project_info:
        app_data["project_info"] = project_info
    
    # 5. 테스트 결과 조회 (AI Service)
    test_result = await msa_client.get_test_result_by_application(application_id)
    if test_result:
        app_data["test_result"] = test_result
    
    return app_data