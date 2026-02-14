from typing import Dict, Any, List
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class ProjectAdapter:
    async def get_project_details(self, project_id: int) -> Dict[str, Any]:
        """
        Project Service API 호출하여 프로젝트 상세 정보 조회
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Project Service는 /projects/{id} 경로 사용 (api/v1 prefix 없음)
                response = await client.get(f"{settings.PROJECT_SERVICE_URL}/projects/{project_id}")
                logger.info(f"Project API response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Project API response: {data}")
                    
                    # recruitment_positions에서 기술 스택 추출
                    tech_stacks = []
                    positions = data.get("recruitment_positions", [])
                    for pos in positions:
                        stacks = pos.get("required_stacks", [])
                        if stacks:
                            # 이미 리스트인 경우 그대로 사용, 문자열인 경우 split
                            if isinstance(stacks, list):
                                tech_stacks.extend(stacks)
                            else:
                                tech_stacks.extend([s.strip() for s in stacks.split(",") if s.strip()])
                    # 중복 제거
                    tech_stacks = list(set(tech_stacks))
                    
                    # API 응답을 포트폴리오 생성에 필요한 형식으로 변환
                    return {
                        "project_id": data.get("id") or data.get("project_id") or project_id,
                        "title": data.get("title") or f"프로젝트_{project_id}",
                        "description": data.get("description") or "",
                        "tech_stacks": tech_stacks,
                        "period": self._format_period(data.get("start_date"), data.get("end_date"))
                    }
                else:
                    logger.warning(f"Project Service returned {response.status_code} for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to fetch project details from Project Service: {e}")
        
        # Fallback: 기본값 반환
        return {
            "project_id": project_id,
            "title": f"프로젝트_{project_id}",
            "description": "",
            "tech_stacks": [],
            "period": "기간 미정"
        }
    
    def _format_period(self, start_date: str, end_date: str) -> str:
        """날짜를 기간 문자열로 변환"""
        if not start_date:
            return "기간 미정"
        try:
            start = start_date[:10] if start_date else ""
            end = end_date[:10] if end_date else "진행중"
            return f"{start} ~ {end}"
        except:
            return "기간 미정"

class TeamAdapter:
    async def get_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Team Service API 호출하여 팀 멤버 목록 조회
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.TEAM_SERVICE_URL}/api/v1/teams/{team_id}/members")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch team members from Team Service: {e}")
        
        return []

class AuthAdapter:
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Auth Service API 호출하여 사용자 프로필 조회
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.AUTH_SERVICE_URL}/auth/users/{user_id}")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch user profile from Auth Service: {e}")
        
        return {
            "user_id": user_id,
            "nickname": "사용자",
            "email": ""
        }

# Singleton Instances
project_adapter = ProjectAdapter()
team_adapter = TeamAdapter()
auth_adapter = AuthAdapter()
