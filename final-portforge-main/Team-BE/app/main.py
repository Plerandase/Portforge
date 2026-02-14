from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from prometheus_fastapi_instrumentator import Instrumentator
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Team Service API",
    description="팀 관리 및 팀스페이스 서비스 - MSA Architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정 (프론트엔드와 다른 MSA 서비스들과 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로메테우스 메트릭 설정 (자동으로 /metrics 엔드포인트 생성)
Instrumentator().instrument(app).expose(app)

# 핵심 API만 등록 - 복잡한 기능들 제거
from app.api.v1.endpoints import teams, team_crud

# 통합 API (프로젝트+팀 생성) - 레거시 호환용
# app.include_router(integration.router, prefix="/api/v1/integration", tags=["integration"])

# 기본 팀 API (간단 버전)
app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])

# MSA 분리용 팀 API (Project Service에서 호출)
app.include_router(team_crud.router, prefix="/api/v1/teams", tags=["team-msa"])

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "service": "Team Service",
        "description": "팀 관리 및 팀스페이스 기능을 제공하는 MSA 서비스",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {
        "status": "healthy",
        "service": "team-service"
    }

# =====================================================
# 프로젝트+팀 통합 정보 조회 API
# FE_latest TeamSpacePage에서 사용
# =====================================================
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from datetime import datetime
import httpx

@app.get("/api/v1/integration/project-team-info/{project_id}")
async def get_project_team_info(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    프로젝트와 팀 통합 정보 조회
    - Project Service에서 프로젝트 정보 가져오기
    - Team Service에서 팀/멤버 정보 가져오기
    """
    from app.models.team import Team, TeamMember
    
    project_data = None
    team_data = None
    members_data = []
    
    # 1. Project Service에서 프로젝트 정보 가져오기
    PROJECT_SERVICE_URL = os.getenv("PROJECT_SERVICE_URL", "http://project-service")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{PROJECT_SERVICE_URL}/projects/{project_id}")
            if resp.status_code == 200:
                result = resp.json()
                project_data = result.get("data", result)
    except Exception as e:
        logger.warning(f"Project Service 조회 실패: {str(e)}")
    
    # 2. 팀 정보 조회
    try:
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if team:
            team_data = {
                "id": team.team_id,
                "name": team.name,
                "project_id": team.project_id
            }
            
            # 3. 팀 멤버 조회
            members_result = await db.execute(
                select(TeamMember).where(TeamMember.team_id == team.team_id)
            )
            members = members_result.scalars().all()
            
            for member in members:
                role_clean = str(member.role).split('.')[-1] if member.role else 'MEMBER'
                position_clean = str(member.position_type).split('.')[-1] if member.position_type else 'UNKNOWN'
                
                members_data.append({
                    "user_id": member.user_id,
                    "nickname": member.user_id,  # 실제로는 Auth Service에서 조회
                    "role": role_clean,
                    "position_type": position_clean
                })
    except Exception as e:
        logger.warning(f"팀 정보 조회 실패: {str(e)}")
    
    # 4. 결과 조합
    if not project_data:
        project_data = {
            "id": project_id,
            "title": f"프로젝트 #{project_id}",
            "type": "PROJECT",
            "status": "진행중",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now().replace(month=datetime.now().month + 1)).strftime("%Y-%m-%d")
        }
    
    if not team_data:
        team_data = {
            "id": project_id,
            "name": f"프로젝트 {project_id} 팀",
            "project_id": project_id
        }
    
    return {
        "status": "success",
        "data": {
            "project": project_data,
            "team": team_data,
            "members": members_data
        }
    }
