"""
MSA 서비스 간 통신을 위한 공통 HTTP 클라이언트
각 서비스에서 이 파일을 복사해서 사용
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class MSAClient:
    """MSA 서비스 간 HTTP 통신 클라이언트"""
    
    def __init__(self):
        # config.py의 settings에서 서비스 URL 읽기
        self.service_urls = {
            "auth": settings.AUTH_SERVICE_URL,
            "project": settings.PROJECT_SERVICE_URL,
            "team": settings.TEAM_SERVICE_URL,
            "ai": settings.AI_SERVICE_URL,
            "support": settings.SUPPORT_SERVICE_URL
        }
        self.timeout = 30.0
    
    async def _make_request(
        self, 
        service: str, 
        endpoint: str, 
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """HTTP 요청 실행"""
        if service not in self.service_urls:
            logger.error(f"Unknown service: {service}")
            return None
            
        url = f"{self.service_urls[service]}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "GET":
                    response = await client.get(url, params=params)
                elif method == "POST":
                    response = await client.post(url, json=data, params=params)
                elif method == "PUT":
                    response = await client.put(url, json=data, params=params)
                elif method == "DELETE":
                    response = await client.delete(url, params=params)
                elif method == "PATCH":
                    response = await client.patch(url, json=data, params=params)
                else:
                    logger.error(f"Unsupported method: {method}")
                    return None
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                else:
                    logger.error(f"Request failed: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"Request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error: {url} - {str(e)}")
            return None

    # =================================================================
    # Auth Service API 호출
    # =================================================================
    async def get_user_detail(self, user_id: str) -> Optional[Dict]:
        """사용자 상세 정보 조회"""
        return await self._make_request("auth", f"/users/{user_id}")
    
    async def get_user_basic(self, user_id: str) -> Optional[Dict]:
        """사용자 기본 정보 조회"""
        return await self._make_request("auth", f"/users/{user_id}/basic")
    
    async def get_users_batch(self, user_ids: List[str]) -> Optional[List[Dict]]:
        """여러 사용자 정보 일괄 조회"""
        return await self._make_request("auth", "/users/batch", "POST", {"user_ids": user_ids})
    
    async def get_user_stacks(self, user_id: str) -> Optional[List[Dict]]:
        """사용자 기술 스택 조회"""
        return await self._make_request("auth", f"/users/{user_id}/stacks")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """email로 user_id 조회 (MSA 내부 통신용)"""
        return await self._make_request("auth", f"/auth/internal/user-by-email", params={"email": email})

    # =================================================================
    # Project Service API 호출
    # =================================================================
    async def get_project_detail(self, project_id: int) -> Optional[Dict]:
        """프로젝트 상세 정보 조회"""
        return await self._make_request("project", f"/projects/{project_id}")
    
    async def get_project_basic(self, project_id: int) -> Optional[Dict]:
        """프로젝트 기본 정보 조회"""
        return await self._make_request("project", f"/projects/{project_id}/basic")
    
    async def get_projects_batch(self, project_ids: List[int]) -> Optional[List[Dict]]:
        """여러 프로젝트 정보 일괄 조회"""
        return await self._make_request("project", "/projects/batch", "POST", {"project_ids": project_ids})
    
    async def get_project_applications(self, project_id: int, status: Optional[str] = None) -> Optional[List[Dict]]:
        """프로젝트 지원서 목록 조회"""
        params = {"status": status} if status else None
        return await self._make_request("project", f"/projects/{project_id}/applications", params=params)
    
    async def get_application_detail(self, application_id: int) -> Optional[Dict]:
        """지원서 상세 정보 조회"""
        return await self._make_request("project", f"/projects/applications/{application_id}")

    # =================================================================
    # AI Service API 호출
    # =================================================================
    async def get_test_result_by_application(self, application_id: int) -> Optional[Dict]:
        """지원서별 테스트 결과 조회"""
        return await self._make_request("ai", f"/ai/test-results/{application_id}")
    
    async def get_user_test_results(self, user_id: str) -> Optional[List[Dict]]:
        """사용자별 테스트 결과 목록 조회"""
        return await self._make_request("ai", f"/ai/test-results/user/{user_id}")
    
    async def get_team_reports(self, team_id: int, report_type: Optional[str] = None) -> Optional[List[Dict]]:
        """팀별 생성된 리포트 목록 조회"""
        params = {"report_type": report_type} if report_type else None
        return await self._make_request("ai", f"/ai/reports/team/{team_id}", params=params)
    
    async def get_report_detail(self, report_id: int) -> Optional[Dict]:
        """리포트 상세 정보 조회"""
        return await self._make_request("ai", f"/ai/reports/{report_id}")
    
    async def get_user_portfolios(self, user_id: str, is_public: Optional[bool] = None) -> Optional[List[Dict]]:
        """사용자별 포트폴리오 목록 조회"""
        params = {"is_public": is_public} if is_public is not None else None
        return await self._make_request("ai", f"/ai/portfolios/user/{user_id}", params=params)
    
    async def generate_test_questions(self, data: Dict[str, Any]) -> Optional[Dict]:
        """AI 서비스 - 테스트 문제 생성"""
        return await self._make_request("ai", "/ai/test/questions", "POST", data)
    
    async def analyze_test_result(self, data: Dict[str, Any]) -> Optional[Dict]:
        """AI 서비스 - 테스트 결과 분석"""
        return await self._make_request("ai", "/ai/test/analyze", "POST", data)

    # =================================================================
    # Project Service 추가 API (프록시용)
    # =================================================================
    async def get_project_list(self) -> Optional[List[Dict]]:
        """프로젝트 목록 조회"""
        return await self._make_request("project", "/projects")
    
    async def apply_to_project(self, project_id: int, application_data: Dict[str, Any]) -> Optional[Dict]:
        """프로젝트 지원"""
        return await self._make_request("project", f"/projects/{project_id}/apply", "POST", application_data)
    
    async def update_application_status(self, application_id: int, status_data: Dict[str, Any]) -> Optional[Dict]:
        """지원서 상태 업데이트"""
        return await self._make_request("project", f"/applications/{application_id}/status", "PATCH", status_data)
    
    async def report_project(self, project_id: int, report_data: Dict[str, Any], user_id: str) -> Optional[Dict]:
        """프로젝트 신고"""
        report_data["user_id"] = user_id
        return await self._make_request("project", f"/projects/{project_id}/report", "POST", report_data)

    # =================================================================
    # Team Service API 호출
    # =================================================================
    async def get_team_detail(self, team_id: int) -> Optional[Dict]:
        """팀 상세 정보 조회"""
        return await self._make_request("team", f"/teams/{team_id}")
    
    async def get_team_members(self, team_id: int) -> Optional[List[Dict]]:
        """팀원 목록 조회"""
        return await self._make_request("team", f"/teams/{team_id}/members")

    # =================================================================
    # Support Service API 호출 (자기 자신 - 필요시 사용)
    # =================================================================
    async def get_chat_logs(self, team_id: int, start_time: str, end_time: str) -> Optional[List[Dict]]:
        """채팅 로그 조회"""
        params = {"start_time": start_time, "end_time": end_time}
        return await self._make_request("support", f"/chat/team/{team_id}/logs", params=params)

# 싱글톤 인스턴스
msa_client = MSAClient()

# =================================================================
# 편의 함수들
# =================================================================
async def get_user_info(user_id: str, detailed: bool = False) -> Optional[Dict]:
    """사용자 정보 조회 (편의 함수)"""
    if detailed:
        return await msa_client.get_user_detail(user_id)
    else:
        return await msa_client.get_user_basic(user_id)

async def get_project_info(project_id: int, detailed: bool = False) -> Optional[Dict]:
    """프로젝트 정보 조회 (편의 함수)"""
    if detailed:
        return await msa_client.get_project_detail(project_id)
    else:
        return await msa_client.get_project_basic(project_id)

async def enrich_data_with_user_info(data_list: List[Dict], user_id_field: str = "user_id") -> List[Dict]:
    """데이터 목록에 사용자 정보 추가"""
    if not data_list:
        return data_list
    
    # 고유한 user_id 추출
    user_ids = list(set([item.get(user_id_field) for item in data_list if item.get(user_id_field)]))
    
    if not user_ids:
        return data_list
    
    # 사용자 정보 일괄 조회
    users_data = await msa_client.get_users_batch(user_ids)
    if not users_data:
        return data_list
    
    # user_id를 키로 하는 딕셔너리 생성
    users_dict = {user["user_id"]: user for user in users_data}
    
    # 데이터에 사용자 정보 추가
    enriched_data = []
    for item in data_list:
        enriched_item = item.copy()
        user_id = item.get(user_id_field)
        if user_id and user_id in users_dict:
            enriched_item["user_info"] = users_dict[user_id]
        enriched_data.append(enriched_item)
    
    return enriched_data
