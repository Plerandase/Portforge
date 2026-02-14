from typing import Dict, Any, List

class ProjectAdapter:
    async def get_project_details(self, project_id: int) -> Dict[str, Any]:
        """
        [MOCK] Project Service API Call
        실제 구현 시: return await http_client.get(f"{PROJECT_SERVICE_URL}/projects/{project_id}")
        """
        # 개발용 더미 데이터
        return {
            "project_id": project_id,
            "title": f"MOCK_프로젝트_{project_id}",
            "description": "이 프로젝트는 AI 기반 협업 플랫폼을 만드는 멋진 프로젝트입니다.",
            "tech_stacks": ["React", "FastAPI", "AWS"],
            "period": "2024.01 ~ 2024.06"
        }

class TeamAdapter:
    async def get_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        """
        [MOCK] Team Service API Call
        """
        return [
            {"user_id": "user_1", "role": "LEADER", "position": "BACKEND"},
            {"user_id": "user_2", "role": "MEMBER", "position": "FRONTEND"}
        ]

class AuthAdapter:
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        [MOCK] Auth Service API Call
        """
        return {
            "user_id": user_id,
            "nickname": "열정적인개발자",
            "email": "dev@example.com"
        }

# Singleton Instances
project_adapter = ProjectAdapter()
team_adapter = TeamAdapter()
auth_adapter = AuthAdapter()
