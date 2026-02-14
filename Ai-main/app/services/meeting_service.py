"""
Meeting Service - AI 회의록 생성 로직

NOTE: 이 서비스는 AI를 사용하여 회의록을 생성합니다.
MeetingSession과 GeneratedReport는 Team-BE에서 관리하므로,
이 서비스는 Team-BE API를 호출하여 데이터를 저장합니다.
"""
from datetime import datetime
from app.core.exceptions import BusinessException, ErrorCode
from app.core.database import aws_manager
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class MeetingService:
    def __init__(self):
        self.team_be_url = settings.TEAM_SERVICE_URL
    
    async def generate_meeting_minutes_from_chat(
        self, 
        chat_text: str, 
        attendees: list = None,
        meeting_date: str = None
    ) -> dict:
        """
        채팅 텍스트로부터 회의록 생성 (AI 호출)
        
        Args:
            chat_text: 채팅 메시지들을 합친 텍스트
            attendees: 참석자 목록 (명시적으로 전달)
            meeting_date: 회의 날짜 (YYYY-MM-DD 형식)
            
        Returns:
            회의록 JSON
        """
        from app.services.ai_service import ai_service
        return await ai_service.generate_minutes_from_chat(chat_text, attendees, meeting_date)
    
    async def get_report_content(self, s3_key: str) -> dict:
        """S3에서 리포트 내용 조회"""
        logger.info(f"Fetching report content from S3: {s3_key}")
        try:
            content = await aws_manager.get_s3_adapter().get_json(s3_key)
            logger.info(f"Successfully fetched content: {list(content.keys()) if isinstance(content, dict) else type(content)}")
            return content
        except Exception as e:
            logger.error(f"Failed to read report content from {s3_key}: {e}")
            raise BusinessException(ErrorCode.NOT_FOUND, f"리포트 파일을 찾을 수 없습니다: {s3_key}")


meeting_service = MeetingService()
