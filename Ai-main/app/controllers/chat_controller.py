"""
Chat Controller - 채팅 메시지 저장 및 조회 API
- 모든 채팅을 DynamoDB에 저장
- 회의록 생성은 기존 meeting_service 사용
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.adapters.dynamodb_adapter import dynamodb_adapter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


class ChatMessageRequest(BaseModel):
    """채팅 메시지 저장 요청"""
    team_id: int
    project_id: int
    user: str
    message: str
    is_in_meeting: bool = False


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    user: str
    msg: str
    time: str
    timestamp: int
    is_in_meeting: bool
    date: str


@router.post("/message", response_model=ChatMessageResponse)
async def save_chat_message(
    request: ChatMessageRequest,
    # current_user: dict = Depends(get_current_user)  # 인증 필요시 주석 해제
):
    """
    채팅 메시지를 DynamoDB에 저장
    - 모든 채팅 메시지는 여기로 전송
    - is_in_meeting=True면 회의 중 메시지로 표시
    """
    try:
        result = await dynamodb_adapter.save_chat_message(
            team_id=request.team_id,
            project_id=request.project_id,
            user=request.user,
            message=request.message,
            is_in_meeting=request.is_in_meeting
        )
        return ChatMessageResponse(**result)
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")
        raise HTTPException(status_code=500, detail=f"메시지 저장 실패: {str(e)}")


@router.get("/messages/{team_id}/{project_id}")
async def get_chat_messages(
    team_id: int,
    project_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    meeting_only: bool = False,
    # current_user: dict = Depends(get_current_user)
):
    """
    채팅 메시지 조회
    - start_date, end_date: YYYY-MM-DD 형식
    - meeting_only: True면 회의 중 메시지만 조회
    """
    try:
        messages = await dynamodb_adapter.get_chat_messages(
            team_id=team_id,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            meeting_only=meeting_only
        )
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        raise HTTPException(status_code=500, detail=f"메시지 조회 실패: {str(e)}")


@router.get("/messages/{team_id}/{project_id}/today")
async def get_today_meeting_messages(
    team_id: int,
    project_id: int,
    # current_user: dict = Depends(get_current_user)
):
    """
    오늘 날짜의 회의 메시지만 조회 (회의록 생성용)
    """
    today = date.today().isoformat()
    try:
        messages = await dynamodb_adapter.get_meeting_messages_by_date(
            team_id=team_id,
            project_id=project_id,
            target_date=today
        )
        return {"date": today, "messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Failed to get today's meeting messages: {e}")
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")
