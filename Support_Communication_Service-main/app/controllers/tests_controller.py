"""
테스트 관련 API - AI Service 프록시
실제 테스트 생성 및 분석은 AI Service(8003)에서 처리
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.utils.msa_client import MSAClient

router = APIRouter()
msa_client = MSAClient()


class TestGenerateRequest(BaseModel):
    position_type: str | None = None
    stack_category: str | None = None
    topic: str | None = None


class TestResultRequest(BaseModel):
    answers: dict
    application_id: int | None = None


@router.post("/generate", response_model=ResponseEnvelope, status_code=201)
async def generate_test(
    payload: TestGenerateRequest, 
    current_user=Depends(get_current_user)
):
    """테스트 생성 - AI Service 프록시"""
    try:
        result = await msa_client.generate_test_questions({
            "position_type": payload.position_type,
            "stack_category": payload.stack_category,
            "topic": payload.topic,
            "user_id": current_user["id"]
        })
        
        if result:
            return ResponseEnvelope(success=True, code="TEST_000", message="Test generated", data=result)
        
        # AI Service 연결 실패 시 기본 응답
        return ResponseEnvelope(
            success=True, 
            code="TEST_000", 
            message="Test generated (fallback)", 
            data={
                "id": 1,
                "topic": payload.topic or "general",
                "questions": [],
                "status": "pending"
            }
        )
    except Exception as e:
        return ResponseEnvelope(success=False, code="TEST_ERR", message=str(e), data=None)


@router.post("/{test_id}/results", response_model=ResponseEnvelope, status_code=201)
async def save_test_result(
    test_id: int, 
    payload: TestResultRequest, 
    current_user=Depends(get_current_user)
):
    """테스트 결과 저장/분석 - AI Service 프록시"""
    try:
        result = await msa_client.analyze_test_result({
            "test_id": test_id,
            "answers": payload.answers,
            "application_id": payload.application_id,
            "user_id": current_user["id"]
        })
        
        if result:
            return ResponseEnvelope(success=True, code="TEST_001", message="Result saved", data=result)
        
        # AI Service 연결 실패 시 기본 응답
        return ResponseEnvelope(
            success=True, 
            code="TEST_001", 
            message="Result saved (fallback)", 
            data={
                "test_id": test_id,
                "answers": payload.answers,
                "user_id": current_user["id"],
                "status": "pending_analysis"
            }
        )
    except Exception as e:
        return ResponseEnvelope(success=False, code="TEST_ERR", message=str(e), data=None)


@router.get("/results/{application_id}", response_model=ResponseEnvelope)
async def get_test_result(
    application_id: int,
    current_user=Depends(get_current_user)
):
    """테스트 결과 조회 - AI Service 프록시"""
    try:
        result = await msa_client.get_test_result_by_application(application_id)
        
        if result:
            return ResponseEnvelope(success=True, code="TEST_002", message="Test result", data=result)
        
        raise HTTPException(status_code=404, detail="테스트 결과를 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        return ResponseEnvelope(success=False, code="TEST_ERR", message=str(e), data=None)
