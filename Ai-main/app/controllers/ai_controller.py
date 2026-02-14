from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.database import get_db 
from app.schemas.ai_schema import (
    QuestionRequest, QuestionResponse, AnalysisRequest, AnalysisResponse,
    PortfolioRequest, PortfolioResponse,
    ApplicantAnalysisRequest, ApplicantAnalysisResponse,
    GradeRequest, GradeResponse
)
from app.services.ai_service import ai_service
from app.services.meeting_service import meeting_service
from app.services.portfolio_service import portfolio_service
from app.repositories.ai_repository import TestRepository
from app.core.exceptions import BusinessException, ErrorCode

router = APIRouter()


class MinutesRequest(BaseModel):
    team_id: int
    project_id: int
    messages: List[Dict[str, Any]]
    attendees: Optional[List[str]] = None  # 명시적 참석자 목록
    meeting_date: Optional[str] = None  # 회의 날짜 (YYYY-MM-DD)

async def get_repository(db: AsyncSession = Depends(get_db)): # type: ignore
    return TestRepository(db)

# --- Test API ---
@router.post("/test/questions", response_model=QuestionResponse)
async def generate_test_questions(
    request: QuestionRequest, 
    repo: TestRepository = Depends(get_repository)
):
    user_id = "test_user_uuid" # [MOCK]
    if not request.stack:
        raise BusinessException(ErrorCode.INVALID_INPUT, "기술 스택(stack)은 필수 입력값입니다.")
    return await ai_service.generate_questions(request, repo, user_id)

@router.post("/test/analyze", response_model=AnalysisResponse)
async def analyze_test_results(
    request: AnalysisRequest,
    repo: TestRepository = Depends(get_repository)
):
    return await ai_service.analyze_results(request, repo, request.user_id)

@router.post("/test/grade", response_model=GradeResponse)
async def grade_test_answer(
    request: GradeRequest
):
    """주관식 답안 AI 채점"""
    result = await ai_service.grade_answer(
        request.question,
        request.user_answer,
        request.model_answer,
        request.grading_criteria or "",
        request.acceptable_keywords
    )
    return GradeResponse(**result)

@router.get("/test/result/{user_id}", response_model=Optional[AnalysisResponse])
async def get_user_test_result(
    user_id: str,
    repo: TestRepository = Depends(get_repository)
):
    return await ai_service.get_latest_result(user_id, repo)

@router.post("/recruit/analyze", response_model=ApplicantAnalysisResponse)
async def analyze_applicants(request: ApplicantAnalysisRequest):
    data = [applicant.model_dump() for applicant in request.applicants]
    analysis = await ai_service.predict_applicant_suitability(data)
    return ApplicantAnalysisResponse(analysis=analysis)

# --- Portfolio API ---
@router.post("/portfolio/generate", response_model=PortfolioResponse)
async def generate_portfolio(
    request: PortfolioRequest,
    db: AsyncSession = Depends(get_db)
):
    result_data = await portfolio_service.generate_portfolio(
        db, 
        request.user_id, 
        request.project_id,
        request.is_team_leader
    )
    return PortfolioResponse(result=result_data)

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """포트폴리오 삭제"""
    result = await portfolio_service.delete_portfolio(db, portfolio_id)
    return result

@router.post("/minutes")
async def generate_minutes(request: MinutesRequest):
    lines: List[str] = []
    attendees_set: set = set()
    
    for msg in request.messages:
        user = msg.get("user") or msg.get("senderName") or "Unknown"
        content = msg.get("msg") or msg.get("message") or msg.get("content") or ""
        if not content:
            continue
        lines.append(f"[{user}] {content}")
        # 메시지에서 참석자 추출 (명시적 목록이 없을 경우 대비)
        if user and user != "Unknown":
            attendees_set.add(user)

    chat_text = "\n".join(lines).strip()
    if not chat_text:
        raise HTTPException(status_code=400, detail="No chat messages to summarize.")

    # 명시적 참석자 목록이 있으면 사용, 없으면 메시지에서 추출한 목록 사용
    final_attendees = request.attendees if request.attendees else list(attendees_set)
    
    # 명시적 날짜가 있으면 사용, 없으면 오늘 날짜
    from datetime import datetime
    final_date = request.meeting_date if request.meeting_date else datetime.now().strftime("%Y-%m-%d")

    result = await meeting_service.generate_meeting_minutes_from_chat(
        chat_text, 
        attendees=final_attendees,
        meeting_date=final_date
    )
    return {"status": "success", "data": result}

# NOTE: 회의록 관련 API는 Team-BE로 이관되었습니다.
# /meeting/start, /meeting/end, /minutes 등의 API는 Team-BE에서 제공합니다.
