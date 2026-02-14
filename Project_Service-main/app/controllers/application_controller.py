from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.schemas.project_recruitment import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, 
    ApplicationListResponse, ApplicationFilters
)
from app.models.project_recruitment import Application, ApplicationStatus
from datetime import datetime

router = APIRouter(prefix="/applications", tags=["Application Management"])

@router.post("", 
    status_code=status.HTTP_201_CREATED, 
    response_model=ApplicationResponse,
    summary="지원서 제출",
    description="특정 프로젝트에 지원서를 제출합니다.",
    responses={
        201: {"description": "지원서 제출 성공"},
        400: {"description": "잘못된 요청 데이터"},
        500: {"description": "서버 내부 오류"}
    }
)
async def create_application(
    project_id: int = Query(..., description="지원할 프로젝트 ID"),
    application_data: ApplicationCreate = ...,
    user_id: str = Query(..., description="지원자 ID (UUID)"),  # This would come from authentication
    db: AsyncSession = Depends(get_db)
):
    """
    ## 지원서 제출
    
    특정 프로젝트의 특정 포지션에 지원서를 제출합니다.
    
    ### 요청 데이터:
    - **project_id**: 지원할 프로젝트 ID
    - **position_type**: 지원할 포지션 타입
    - **prefer_stacks**: 선호하는 기술 스택 (선택사항)
    - **message**: 지원 메시지
    - **user_id**: 지원자 ID
    
    ### 반환값:
    - 제출된 지원서 정보
    """
    try:
        # Create application
        application = Application(
            project_id=project_id,
            user_id=user_id,
            position_type=application_data.position_type,
            prefer_stacks=application_data.prefer_stacks,
            message=application_data.message,
            status=ApplicationStatus.PENDING
        )
        
        db.add(application)
        await db.commit()
        await db.refresh(application)
        
        return ApplicationResponse.from_orm(application)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", 
    response_model=ApplicationListResponse,
    summary="프로젝트 지원서 목록 조회",
    description="특정 프로젝트에 제출된 모든 지원서를 조회합니다. (팀장 전용)",
    responses={
        200: {"description": "지원서 목록 조회 성공"},
        404: {"description": "프로젝트를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def get_project_applications(
    project_id: int = Path(..., description="조회할 프로젝트 ID"),
    status: Optional[str] = Query(None, description="지원서 상태 필터 (PENDING/ACCEPTED/REJECTED)"),
    position_type: Optional[str] = Query(None, description="포지션 타입 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db)
):
    """
    ## 프로젝트 지원서 목록 조회
    
    특정 프로젝트에 제출된 모든 지원서를 조회합니다.
    팀장만 접근 가능한 기능입니다.
    
    ### 경로 파라미터:
    - **project_id**: 조회할 프로젝트 ID
    
    ### 쿼리 파라미터:
    - **status**: 지원서 상태로 필터링
    - **position_type**: 포지션 타입으로 필터링
    - **page**: 페이지 번호
    - **size**: 페이지당 항목 수
    
    ### 반환값:
    - 지원서 목록과 통계 정보 (대기/승인/거절 개수)
    """
    try:
        from sqlalchemy import select, func
        
        # Build query
        query = select(Application).where(Application.project_id == project_id)
        
        if status:
            query = query.where(Application.status == ApplicationStatus(status))
        if position_type:
            query = query.where(Application.position_type == position_type)
        
        # Get total count
        count_query = select(func.count(Application.application_id)).where(Application.project_id == project_id)
        if status:
            count_query = count_query.where(Application.status == ApplicationStatus(status))
        if position_type:
            count_query = count_query.where(Application.position_type == position_type)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get status counts
        pending_count_result = await db.execute(
            select(func.count(Application.application_id))
            .where(Application.project_id == project_id, Application.status == ApplicationStatus.PENDING)
        )
        accepted_count_result = await db.execute(
            select(func.count(Application.application_id))
            .where(Application.project_id == project_id, Application.status == ApplicationStatus.ACCEPTED)
        )
        rejected_count_result = await db.execute(
            select(func.count(Application.application_id))
            .where(Application.project_id == project_id, Application.status == ApplicationStatus.REJECTED)
        )
        
        pending_count = pending_count_result.scalar()
        accepted_count = accepted_count_result.scalar()
        rejected_count = rejected_count_result.scalar()
        
        # Apply pagination
        query = query.order_by(Application.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        
        result = await db.execute(query)
        applications = result.scalars().all()
        
        return ApplicationListResponse(
            applications=[ApplicationResponse.from_orm(app) for app in applications],
            total=total,
            pending_count=pending_count,
            accepted_count=accepted_count,
            rejected_count=rejected_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application_detail(application_id: int, db: AsyncSession = Depends(get_db)):
    """Get application detail"""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Application).where(Application.application_id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return ApplicationResponse.from_orm(application)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    status_data: ApplicationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update application status (accept/reject)"""
    try:
        from sqlalchemy import select, update
        
        # Check if application exists
        result = await db.execute(
            select(Application).where(Application.application_id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Update status
        await db.execute(
            update(Application)
            .where(Application.application_id == application_id)
            .values(status=status_data.status, updated_at=datetime.utcnow())
        )
        await db.commit()
        
        # Return updated application
        result = await db.execute(
            select(Application).where(Application.application_id == application_id)
        )
        updated_application = result.scalar_one()
        
        return ApplicationResponse.from_orm(updated_application)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{application_id}")
async def delete_application(application_id: int, db: AsyncSession = Depends(get_db)):
    """Delete application"""
    try:
        from sqlalchemy import delete
        
        result = await db.execute(
            delete(Application).where(Application.application_id == application_id)
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return {"message": "Application deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))