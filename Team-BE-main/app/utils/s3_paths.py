"""
S3 경로 관리를 위한 공용 모듈
모든 MSA 서비스에서 동일한 경로 규칙을 사용하도록 함

버킷 구조:
- portforge-team: 팀 관련 파일 (공유 파일, 회의록, AI 생성물)
- portforge-front: 프론트엔드 에셋 (프로필 이미지, 썸네일)
- portforge-log: 서비스 로그
"""
from datetime import datetime
from typing import Optional


class S3PathManager:
    """
    S3 경로 생성 관리자
    
    portforge-team 버킷 경로 구조:
    - teams/{team_id}/
        - shared/                           # 팀 공유 파일
        - meetings/{date}/                  # 회의록
        - chats/{date}/                     # 채팅 로그 백업
        - reports/{report_type}/            # AI 생성 리포트
    - ai/
        - tests/{test_id}/                  # AI 생성 테스트 문제
        - analysis/{result_id}/             # 분석 결과
        - portfolios/{user_id}/             # AI 생성 포트폴리오
    """
    
    def __init__(self):
        pass
    
    # =========================================================
    # Team 관련 경로 (portforge-team 버킷)
    # =========================================================
    def team_base(self, team_id: int) -> str:
        """팀 기본 경로"""
        return f"teams/{team_id}/"
    
    def team_shared_file(self, team_id: int, filename: str) -> str:
        """팀 공유 파일 경로"""
        return f"teams/{team_id}/shared/{filename}"
    
    def team_meeting(self, team_id: int, date: Optional[str] = None) -> str:
        """회의록 경로"""
        if date is None:
            from .timezone import format_kst_date
            date = format_kst_date()
        return f"teams/{team_id}/meetings/{date}.json"
    
    def team_meeting_audio(self, team_id: int, session_id: int) -> str:
        """회의 오디오 녹음 경로"""
        from .timezone import format_kst_timestamp
        timestamp = format_kst_timestamp()
        return f"teams/{team_id}/meetings/audio/{session_id}_{timestamp}.webm"
    
    def team_chat_backup(self, team_id: int, date: Optional[str] = None) -> str:
        """채팅 로그 백업 경로"""
        if date is None:
            from .timezone import format_kst_date
            date = format_kst_date()
        return f"teams/{team_id}/chats/{date}.json"
    
    def team_report(self, team_id: int, report_id: int, report_type: str) -> str:
        """AI 생성 리포트 경로"""
        from .timezone import format_kst_timestamp
        timestamp = format_kst_timestamp()
        return f"teams/{team_id}/reports/{report_type}/{report_id}_{timestamp}.json"
    
    # =========================================================
    # AI 관련 경로 (portforge-team 버킷 내 ai/ 디렉토리)
    # =========================================================
    def ai_test_questions(self, test_id: int) -> str:
        """AI 생성 테스트 문제 경로"""
        return f"ai/tests/{test_id}/questions.json"
    
    def ai_test_result(self, result_id: int) -> str:
        """테스트 결과 분석 경로"""
        return f"ai/analysis/{result_id}/result.json"
    
    def ai_portfolio_generation(self, user_id: str, portfolio_id: int) -> str:
        """AI 생성 포트폴리오 경로"""
        from .timezone import format_kst_timestamp
        timestamp = format_kst_timestamp()
        return f"ai/portfolios/{user_id}/{portfolio_id}_{timestamp}.json"
    
    # =========================================================
    # 유틸리티
    # =========================================================
    def parse_path(self, s3_key: str) -> dict:
        """S3 경로 파싱"""
        parts = s3_key.split('/')
        result = {"raw": s3_key}
        
        if len(parts) >= 2:
            result["category"] = parts[0]  # teams, ai
            result["id"] = parts[1]        # team_id, etc.
            
        if len(parts) >= 3:
            result["subcategory"] = parts[2]  # shared, meetings, etc.
            
        return result


# 싱글톤 인스턴스
s3_path_manager = S3PathManager()


# =========================================================
# 편의 함수들
# =========================================================
def get_team_s3_key(team_id: int) -> str:
    """팀 기본 S3 키 생성"""
    return s3_path_manager.team_base(team_id)


def get_meeting_s3_key(team_id: int, date: str = None) -> str:
    """회의록 S3 키 생성"""
    return s3_path_manager.team_meeting(team_id, date)


def get_chat_backup_s3_key(team_id: int, date: str = None) -> str:
    """채팅 백업 S3 키 생성"""
    return s3_path_manager.team_chat_backup(team_id, date)


def get_shared_file_s3_key(team_id: int, filename: str) -> str:
    """공유 파일 S3 키 생성"""
    return s3_path_manager.team_shared_file(team_id, filename)


def get_report_s3_key(team_id: int, report_id: int, report_type: str = "meeting_minutes") -> str:
    """리포트 S3 키 생성"""
    return s3_path_manager.team_report(team_id, report_id, report_type)


def get_file_upload_s3_key(team_id: int, filename: str) -> str:
    """파일 업로드 S3 키 생성"""
    return s3_path_manager.team_shared_file(team_id, filename)
