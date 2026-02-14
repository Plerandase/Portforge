from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.ai_model import TestResult, Portfolio
from app.schemas.ai import TestResultResponse, PortfolioResponse
from app.core.database import get_db

router = APIRouter(tags=["ai"])

@router.get("/test-results/{application_id}", response_model=TestResultResponse)
async def get_test_result_by_application(
    application_id: int,
    db: AsyncSession = Depends(get_db)
):
    """지원서별 테스트 결과 조회"""
    query = select(TestResult).where(TestResult.application_id == application_id)
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    return TestResultResponse(
        result_id=test_result.result_id,
        user_id=test_result.user_id,
        project_id=test_result.project_id,
        application_id=test_result.application_id,
        test_type=test_result.test_type,
        score=test_result.score,
        feedback=test_result.feedback,
        created_at=test_result.created_at
    )


@router.get("/test-results/by-user-project/{user_id}/{project_id}", response_model=TestResultResponse)
async def get_test_result_by_user_project(
    user_id: str,
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """user_id + project_id로 테스트 결과 조회 (application_id 연결 실패 시 fallback용)"""
    query = select(TestResult).where(
        TestResult.user_id == user_id,
        TestResult.project_id == project_id
    ).order_by(TestResult.created_at.desc())
    
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    return TestResultResponse(
        result_id=test_result.result_id,
        user_id=test_result.user_id,
        project_id=test_result.project_id,
        application_id=test_result.application_id,
        test_type=test_result.test_type,
        score=test_result.score,
        feedback=test_result.feedback,
        created_at=test_result.created_at
    )

@router.get("/test-results/user/{user_id}", response_model=List[TestResultResponse])
async def get_user_test_results(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """사용자별 테스트 결과 목록 조회"""
    query = select(TestResult).where(TestResult.user_id == user_id)
    result = await db.execute(query)
    test_results = result.scalars().all()
    
    return [
        TestResultResponse(
            result_id=tr.result_id,
            user_id=tr.user_id,
            project_id=tr.project_id,
            application_id=tr.application_id,
            test_type=tr.test_type,
            score=tr.score,
            feedback=tr.feedback,
            created_at=tr.created_at
        ) for tr in test_results
    ]

@router.patch("/test-results/link-application")
async def link_test_result_to_application(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """테스트 결과에 application_id를 연결 (지원서 제출 후 호출)"""
    user_id = data.get("user_id")
    project_id = data.get("project_id")
    application_id = data.get("application_id")
    
    if not all([user_id, project_id, application_id]):
        raise HTTPException(status_code=400, detail="user_id, project_id, application_id are required")
    
    # 해당 사용자의 해당 프로젝트 테스트 결과 찾기
    query = select(TestResult).where(
        TestResult.user_id == user_id,
        TestResult.project_id == project_id,
        TestResult.application_id == None  # 아직 연결 안 된 것만
    ).order_by(TestResult.created_at.desc())
    
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        # 테스트 결과가 없어도 에러 안 냄 (테스트 없이 지원하는 경우)
        return {"status": "no_test_result", "message": "No unlinked test result found"}
    
    test_result.application_id = application_id
    await db.commit()
    
    return {"status": "success", "result_id": test_result.result_id, "application_id": application_id}


# =====================================================
# Portfolio APIs
# =====================================================
@router.get("/portfolios/user/{user_id}", response_model=List[PortfolioResponse])
async def get_user_portfolios(
    user_id: str,
    is_public: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """사용자별 포트폴리오 목록 조회"""
    query = select(Portfolio).where(Portfolio.user_id == user_id)
    
    if is_public is not None:
        query = query.where(Portfolio.is_public == is_public)
    
    result = await db.execute(query)
    portfolios = result.scalars().all()
    
    return [
        PortfolioResponse(
            portfolio_id=portfolio.portfolio_id,
            user_id=portfolio.user_id,
            project_id=portfolio.project_id,
            title=portfolio.title,
            summary=portfolio.summary,
            role_description=portfolio.role_description,
            problem_solving=portfolio.problem_solving,
            tech_stack_usage=portfolio.tech_stack_usage,
            growth_point=portfolio.growth_point,
            thumbnail_url=portfolio.thumbnail_url,
            is_public=portfolio.is_public,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at
        ) for portfolio in portfolios
    ]

@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio_detail(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """포트폴리오 상세 조회"""
    query = select(Portfolio).where(Portfolio.portfolio_id == portfolio_id)
    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    return PortfolioResponse(
        portfolio_id=portfolio.portfolio_id,
        user_id=portfolio.user_id,
        project_id=portfolio.project_id,
        title=portfolio.title,
        summary=portfolio.summary,
        role_description=portfolio.role_description,
        problem_solving=portfolio.problem_solving,
        tech_stack_usage=portfolio.tech_stack_usage,
        growth_point=portfolio.growth_point,
        thumbnail_url=portfolio.thumbnail_url,
        is_public=portfolio.is_public,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at
    )

@router.patch("/portfolios/{portfolio_id}/links")
async def update_portfolio_links(
    portfolio_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """포트폴리오 외부 링크 업데이트"""
    query = select(Portfolio).where(Portfolio.portfolio_id == portfolio_id)
    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    external_links = data.get("external_links", "")
    portfolio.external_links = external_links
    
    await db.commit()
    await db.refresh(portfolio)
    
    return {
        "status": "success",
        "portfolio_id": portfolio.portfolio_id,
        "external_links": portfolio.external_links
    }

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """포트폴리오 삭제 (S3 파일 포함)"""
    import boto3
    import json
    from app.core.config import settings
    
    query = select(Portfolio).where(Portfolio.portfolio_id == portfolio_id)
    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # S3에서 관련 파일 삭제 (썸네일 등)
    if portfolio.thumbnail_url:
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            # URL에서 S3 키 추출
            # 예: https://bucket.s3.region.amazonaws.com/key -> key
            if settings.S3_BUCKET_TEAM in portfolio.thumbnail_url:
                s3_key = portfolio.thumbnail_url.split(f"{settings.S3_BUCKET_TEAM}/")[-1]
                s3_client.delete_object(Bucket=settings.S3_BUCKET_TEAM, Key=s3_key)
        except Exception as e:
            # S3 삭제 실패해도 DB는 삭제 진행
            print(f"S3 파일 삭제 실패 (무시): {e}")
    
    # DB에서 포트폴리오 삭제
    await db.delete(portfolio)
    await db.commit()
    
    return {
        "status": "success",
        "message": "Portfolio deleted successfully",
        "portfolio_id": portfolio_id
    }
