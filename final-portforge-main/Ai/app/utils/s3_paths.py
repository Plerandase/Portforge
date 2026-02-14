"""
S3 경로 관리를 위한 공용 모듈
모든 MSA 서비스에서 동일한 경로 규칙을 사용하도록 함
"""
from datetime import datetime
from typing import Optional


class S3PathManager:
    """
    S3 경로 생성 관리자
    
    경로 구조:
    - portforge/
        - users/{user_id}/
            - profile/                      # 프로필 이미지
            - portfolios/{portfolio_id}/    # 포트폴리오 파일
        - teams/{team_id}/
            - info/                         # 팀 기본 정보
            - meetings/{date}/              # 회의록
            - chats/{date}/                 # 채팅 로그 백업
            - files/{file_id}/              # 공유 파일
            - reports/{report_id}/          # AI 생성 리포트
        - projects/{project_id}/
            - info/                         # 프로젝트 기본 정보
            - thumbnails/                   # 프로젝트 썸네일
        - ai/
            - tests/{test_id}/              # AI 생성 테스트 문제
            - analysis/{result_id}/         # 분석 결과
    """
    
    def __init__(self, prefix: str = "portforge"):
        self.prefix = prefix
    
    # =========================================================
    # User 관련 경로
    # =========================================================
    def user_profile_image(self, user_id: str, filename: str) -> str:
        """사용자 프로필 이미지 경로"""
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        return f"{self.prefix}/users/{user_id}/profile/avatar.{ext}"
    
    def user_portfolio(self, user_id: str, portfolio_id: int, filename: str) -> str:
        """사용자 포트폴리오 파일 경로"""
        return f"{self.prefix}/users/{user_id}/portfolios/{portfolio_id}/{filename}"
    
    def user_portfolio_thumbnail(self, user_id: str, portfolio_id: int) -> str:
        """포트폴리오 썸네일 경로"""
        return f"{self.prefix}/users/{user_id}/portfolios/{portfolio_id}/thumbnail.jpg"
    
    # =========================================================
    # Team 관련 경로
    # =========================================================
    def team_base(self, team_id: int) -> str:
        """팀 기본 경로 (DB의 s3_key 필드용)"""
        return f"{self.prefix}/teams/{team_id}/"
    
    def team_info(self, team_id: int) -> str:
        """팀 정보 파일 경로"""
        return f"{self.prefix}/teams/{team_id}/info/team_info.json"
    
    def team_meeting(self, team_id: int, date: Optional[str] = None) -> str:
        """회의록 경로"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return f"{self.prefix}/teams/{team_id}/meetings/{date}.json"
    
    def team_meeting_audio(self, team_id: int, session_id: int) -> str:
        """회의 오디오 녹음 경로"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.prefix}/teams/{team_id}/meetings/audio/{session_id}_{timestamp}.webm"
    
    def team_chat_backup(self, team_id: int, date: Optional[str] = None) -> str:
        """채팅 로그 백업 경로"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return f"{self.prefix}/teams/{team_id}/chats/{date}.json"
    
    def team_shared_file(self, team_id: int, file_id: int, filename: str) -> str:
        """팀 공유 파일 경로"""
        return f"{self.prefix}/teams/{team_id}/files/{file_id}/{filename}"
    
    def team_report(self, team_id: int, report_id: int, report_type: str) -> str:
        """AI 생성 리포트 경로"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.prefix}/teams/{team_id}/reports/{report_type}/{report_id}_{timestamp}.json"
    
    # =========================================================
    # Project 관련 경로
    # =========================================================
    def project_thumbnail(self, project_id: int, filename: str = "thumbnail.jpg") -> str:
        """프로젝트 썸네일 경로"""
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        return f"{self.prefix}/projects/{project_id}/thumbnails/main.{ext}"
    
    def project_info(self, project_id: int) -> str:
        """프로젝트 정보 파일 경로"""
        return f"{self.prefix}/projects/{project_id}/info/project_info.json"
    
    # =========================================================
    # AI 관련 경로
    # =========================================================
    def ai_test_questions(self, test_id: int) -> str:
        """AI 생성 테스트 문제 경로"""
        return f"{self.prefix}/ai/tests/{test_id}/questions.json"
    
    def ai_test_result(self, result_id: int) -> str:
        """테스트 결과 분석 경로"""
        return f"{self.prefix}/ai/analysis/{result_id}/result.json"
    
    def ai_portfolio_generation(self, user_id: str, portfolio_id: int) -> str:
        """AI 생성 포트폴리오 경로"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.prefix}/ai/portfolios/{user_id}/{portfolio_id}_{timestamp}.json"
    
    # =========================================================
    # 유틸리티
    # =========================================================
    def parse_path(self, s3_key: str) -> dict:
        """S3 경로 파싱"""
        parts = s3_key.replace(f"{self.prefix}/", "").split('/')
        result = {"raw": s3_key, "prefix": self.prefix}
        
        if len(parts) >= 2:
            result["category"] = parts[0]  # users, teams, projects, ai
            result["id"] = parts[1]        # user_id, team_id, etc.
            
        if len(parts) >= 3:
            result["subcategory"] = parts[2]  # profile, meetings, files, etc.
            
        return result
    
    def get_presigned_url_path(self, operation: str, **kwargs) -> str:
        """
        Presigned URL 생성용 경로 반환
        
        Args:
            operation: "upload_profile", "upload_file", "get_meeting", etc.
            **kwargs: 필요한 ID 값들
        """
        operations = {
            "upload_profile": lambda: self.user_profile_image(kwargs["user_id"], kwargs.get("filename", "avatar.jpg")),
            "upload_file": lambda: self.team_shared_file(kwargs["team_id"], kwargs["file_id"], kwargs["filename"]),
            "get_meeting": lambda: self.team_meeting(kwargs["team_id"], kwargs.get("date")),
            "upload_portfolio": lambda: self.user_portfolio(kwargs["user_id"], kwargs["portfolio_id"], kwargs["filename"]),
        }
        
        if operation in operations:
            return operations[operation]()
        raise ValueError(f"Unknown operation: {operation}")


# 싱글톤 인스턴스
s3_path_manager = S3PathManager()


# =========================================================
# 편의 함수들
# =========================================================
def get_team_s3_key(team_id: int) -> str:
    """팀 기본 S3 키 생성 (팀 생성 시 사용)"""
    return s3_path_manager.team_base(team_id)


def get_meeting_s3_key(team_id: int, date: str = None) -> str:
    """회의록 S3 키 생성"""
    return s3_path_manager.team_meeting(team_id, date)


def get_chat_backup_s3_key(team_id: int, date: str = None) -> str:
    """채팅 백업 S3 키 생성"""
    return s3_path_manager.team_chat_backup(team_id, date)


def get_file_upload_s3_key(team_id: int, file_id: int, filename: str) -> str:
    """파일 업로드 S3 키 생성"""
    return s3_path_manager.team_shared_file(team_id, file_id, filename)


def get_profile_image_s3_key(user_id: str, filename: str = "avatar.jpg") -> str:
    """프로필 이미지 S3 키 생성"""
    return s3_path_manager.user_profile_image(user_id, filename)


def get_report_s3_key(team_id: int, report_id: int, report_type: str = "meeting_minutes") -> str:
    """리포트 S3 키 생성"""
    return s3_path_manager.team_report(team_id, report_id, report_type)
