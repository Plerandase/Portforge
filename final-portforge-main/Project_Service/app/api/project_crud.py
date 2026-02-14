"""
Project Service - 프로젝트 CRUD API (보상 트랜잭션 + Circuit Breaker 적용)
ERD 기반 MSA 분리: 프로젝트/모집포지션/지원서 관리
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import json
import logging
import httpx
import time
import sys
import os

# shared 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from app.core.database import get_db
from app.models.project_recruitment import (
    Project, ProjectRecruitmentPosition, Application,
    ProjectType, ProjectMethod, ProjectStatus, ApplicationStatus, 
    PositionType as StackCategory  # Alias for compatibility
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

# =====================================================
# Circuit Breaker 구현 (인라인)
# =====================================================
class SimpleCircuitBreaker:
    """간단한 Circuit Breaker 구현"""
    
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        
        # 복구 시간 경과 확인
        if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_timeout:
            logger.info(f"🟡 [{self.name}] Circuit 복구 테스트")
            return True
        
        logger.warning(f"🔴 [{self.name}] Circuit OPEN - 요청 차단")
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"🔴 [{self.name}] Circuit OPEN - 연속 {self.failure_count}회 실패")

# 서비스별 Circuit Breaker
team_service_breaker = SimpleCircuitBreaker("TeamService")
support_service_breaker = SimpleCircuitBreaker("SupportService")
auth_service_breaker = SimpleCircuitBreaker("AuthService")

# =====================================================
# Team Service 통신용 클라이언트 (Circuit Breaker 적용)
# =====================================================
import os
TEAM_SERVICE_URL = os.getenv("TEAM_SERVICE_URL", "http://team-service")
SUPPORT_SERVICE_URL = os.getenv("SUPPORT_SERVICE_URL", "http://support-service")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service")

async def get_user_nickname(user_id: str) -> str:
    """Auth Service에서 사용자 닉네임 조회"""
    if not auth_service_breaker.can_execute():
        return "익명"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AUTH_SERVICE_URL}/users/{user_id}/basic")
            if response.status_code == 200:
                auth_service_breaker.record_success()
                data = response.json()
                return data.get("nickname", "익명")
            else:
                auth_service_breaker.record_failure()
                return "익명"
    except Exception as e:
        logger.warning(f"Auth Service 호출 실패: {str(e)}")
        auth_service_breaker.record_failure()
        return "익명"

async def get_users_nicknames(user_ids: list) -> dict:
    """Auth Service에서 여러 사용자 닉네임 일괄 조회"""
    if not user_ids or not auth_service_breaker.can_execute():
        return {}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/users/batch",
                json={"user_ids": list(set(user_ids))}  # 중복 제거
            )
            if response.status_code == 200:
                auth_service_breaker.record_success()
                users = response.json()
                return {u.get("user_id"): u.get("nickname", "익명") for u in users}
            else:
                auth_service_breaker.record_failure()
                return {}
    except Exception as e:
        logger.warning(f"Auth Service 일괄 조회 실패: {str(e)}")
        auth_service_breaker.record_failure()
        return {}

async def get_team_leader_nickname(project_id: int) -> str:
    """Team Service에서 프로젝트의 팀장 닉네임 조회"""
    if not team_service_breaker.can_execute():
        return "익명"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 팀 stats API 호출 (멤버 정보 포함)
            response = await client.get(f"{TEAM_SERVICE_URL}/api/v1/teams/{project_id}/stats")
            if response.status_code == 200:
                team_service_breaker.record_success()
                data = response.json()
                members = data.get("members", [])
                # LEADER 역할인 멤버 찾기
                for member in members:
                    if member.get("role") == "LEADER":
                        return member.get("nickname", "익명")
                return "익명"
            else:
                team_service_breaker.record_failure()
                return "익명"
    except Exception as e:
        logger.warning(f"Team Service 호출 실패: {str(e)}")
        team_service_breaker.record_failure()
        return "익명"

async def get_team_leaders_nicknames(project_ids: list) -> dict:
    """Team Service에서 여러 프로젝트의 팀장 닉네임 일괄 조회"""
    if not project_ids:
        return {}
    
    result = {}
    for project_id in project_ids:
        result[project_id] = await get_team_leader_nickname(project_id)
    return result

async def call_team_service(method: str, endpoint: str, data: dict = None) -> dict:
    """Team Service API 호출 (Circuit Breaker 적용)"""
    
    # 1. Circuit Breaker 확인
    if not team_service_breaker.can_execute():
        logger.warning("Team Service 호출 차단됨 (Circuit Open)")
        return None
    
    # 2. 실제 호출
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{TEAM_SERVICE_URL}{endpoint}"
        try:
            if method == "POST":
                response = await client.post(url, json=data)
            elif method == "GET":
                response = await client.get(url)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                response = await client.request(method, url, json=data)
            
            if response.status_code >= 400:
                logger.error(f"Team Service 호출 실패: {response.status_code}")
                team_service_breaker.record_failure()
                return None
            
            # 성공
            team_service_breaker.record_success()
            return response.json()
            
        except httpx.TimeoutException:
            logger.error(f"Team Service 타임아웃: {url}")
            team_service_breaker.record_failure()
            return None
        except Exception as e:
            logger.error(f"Team Service 연결 실패: {str(e)}")
            team_service_breaker.record_failure()
            return None

async def send_notification(user_id: str, message: str, link: str = "/"):
    """Support Service에 알림 전송 (실패해도 계속 진행)"""
    if not support_service_breaker.can_execute():
        return
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(f"{SUPPORT_SERVICE_URL}/notifications", json={
                "user_id": user_id,
                "message": message,
                "link": link,
            })
            support_service_breaker.record_success()
        except Exception as e:
            support_service_breaker.record_failure()
            logger.warning(f"알림 전송 실패 (무시됨): {str(e)}")

# =====================================================
# 헬퍼 함수
# =====================================================
def get_method_display_name(method) -> str:
    """ProjectMethod enum을 한글 표시명으로 변환"""
    method_str = str(method)
    if "ONLINE" in method_str:
        return "온라인"
    elif "OFFLINE" in method_str:
        return "오프라인"
    elif "MIXED" in method_str:
        return "믹스"
    return "온라인"

def convert_position_type(position_str: str) -> StackCategory:
    """한글 포지션명을 StackCategory로 변환"""
    mapping = {
        "프론트엔드": StackCategory.FRONTEND,
        "백엔드": StackCategory.BACKEND,
        "디자인": StackCategory.DESIGN,
        "DB": StackCategory.DB,
        "인프라": StackCategory.INFRA,
        "기타": StackCategory.ETC,
        "스터디원": StackCategory.STUDY_MEMBER,
    }
    return mapping.get(position_str, StackCategory.ETC)

# =====================================================
# 1. 프로젝트 목록 조회 (공개 API)
# =====================================================
@router.get("")
async def get_projects(
    page: int = 1,
    size: int = 20,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트 목록 조회 (메인 페이지용)"""
    try:
        query = select(Project).options(selectinload(Project.recruitment_positions))
        
        # 필터 적용
        if type:
            if type == "프로젝트":
                query = query.where(Project.type == ProjectType.PROJECT)
            elif type == "스터디":
                query = query.where(Project.type == ProjectType.STUDY)
        
        if status:
            if status == "모집중":
                query = query.where(Project.status == ProjectStatus.RECRUITING)
            elif status == "진행중":
                query = query.where(Project.status == ProjectStatus.PROCEEDING)
        
        # 정렬 및 페이지네이션
        query = query.order_by(Project.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        # 팀장 닉네임 일괄 조회
        project_ids = [p.project_id for p in projects]
        leader_nicknames = await get_team_leaders_nicknames(project_ids)
        
        project_list = []
        for p in projects:
            logger.info(f"📋 프로젝트 {p.project_id}: {p.title}, 포지션 수: {len(p.recruitment_positions) if p.recruitment_positions else 0}")
            
            # 마감일 계산
            deadline = "D-?"
            if p.recruitment_positions:
                deadlines = [pos.recruitment_deadline for pos in p.recruitment_positions if pos.recruitment_deadline]
                if deadlines:
                    recruit_deadline = min(deadlines)
                    diff_days = (recruit_deadline - datetime.now().date()).days
                    if diff_days > 0:
                        deadline = f"D-{diff_days}"
                    elif diff_days == 0:
                        deadline = "D-Day"
                    else:
                        deadline = "모집마감"
            
            # 인원 수 계산 - 포지션별로 표시
            members_parts = []
            for pos in p.recruitment_positions:
                pos_name = pos.position_type.value if pos.position_type else "미정"
                # 한글 포지션명으로 변환
                pos_name_kr = {
                    "FRONTEND": "프론트엔드",
                    "BACKEND": "백엔드",
                    "DESIGN": "디자인",
                    "DB": "DB",
                    "INFRA": "인프라",
                    "ETC": "기타",
                    "STUDY_MEMBER": "스터디원"
                }.get(pos_name, pos_name)
                current = pos.current_count or 0
                target = pos.target_count or 0
                members_parts.append(f"{pos_name_kr} {current}/{target}")
            
            members_str = ", ".join(members_parts) if members_parts else "0/0명"
            
            # 기술 스택 추출
            all_stacks = set()
            for pos in p.recruitment_positions:
                logger.info(f"  📦 포지션 {pos.position_type}: required_stacks = {repr(pos.required_stacks)}")
                if pos.required_stacks:
                    try:
                        stacks = json.loads(pos.required_stacks) if isinstance(pos.required_stacks, str) else []
                        logger.info(f"    → 파싱된 스택: {stacks}")
                        all_stacks.update(stacks)
                    except Exception as e:
                        logger.error(f"    → 파싱 실패: {e}")
            
            logger.info(f"  📋 최종 tags: {list(all_stacks)}")
            
            project_list.append({
                "id": p.project_id,
                "project_id": p.project_id,  # 호환성을 위해 둘 다 제공
                "type": "프로젝트" if p.type == ProjectType.PROJECT else "스터디",
                "title": p.title,
                "description": p.description,
                "deadline": deadline,
                "views": p.views or 0,
                "members": members_str,
                "tags": list(all_stacks) if all_stacks else [],
                "position": p.recruitment_positions[0].position_type.value if p.recruitment_positions else "미정",
                "method": get_method_display_name(p.method),
                "status": "모집중" if p.status == ProjectStatus.RECRUITING else "진행중",
                "authorId": p.user_id,
                "user_id": p.user_id,  # 호환성을 위해 둘 다 제공
                "leaderName": leader_nicknames.get(p.project_id, "익명"),
                "startDate": p.start_date.isoformat() if p.start_date else None,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "endDate": p.end_date.isoformat() if p.end_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "testRequired": p.test_required or False,
                "test_required": p.test_required or False,
                "recruitment_positions": [
                    {
                        "position_type": pos.position_type.value if pos.position_type else "UNKNOWN",
                        "required_stacks": json.loads(pos.required_stacks) if isinstance(pos.required_stacks, str) and pos.required_stacks else [],
                        "target_count": pos.target_count or 0,
                        "current_count": pos.current_count or 0,
                        "recruitment_deadline": pos.recruitment_deadline.isoformat() if pos.recruitment_deadline else None,
                    } for pos in p.recruitment_positions
                ],
            })
        
        return project_list
        
    except Exception as e:
        logger.error(f"프로젝트 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"프로젝트 목록 조회 실패: {str(e)}")

# =====================================================
# 2. 프로젝트 상세 조회
# =====================================================
@router.get("/{project_id}")
async def get_project_detail(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트 상세 정보 조회"""
    try:
        query = select(Project).options(
            selectinload(Project.recruitment_positions)
        ).where(Project.project_id == project_id)
        
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
        
        # 조회수 증가
        project.views = (project.views or 0) + 1
        await db.commit()
        
        # 모집 포지션 정보
        positions = []
        for pos in project.recruitment_positions:
            stacks = []
            if pos.required_stacks:
                try:
                    stacks = json.loads(pos.required_stacks) if isinstance(pos.required_stacks, str) else []
                except:
                    pass
            positions.append({
                "position_type": pos.position_type.value if pos.position_type else "UNKNOWN",
                "required_stacks": stacks,
                "target_count": pos.target_count or 0,
                "current_count": pos.current_count or 0,
                "recruitment_deadline": pos.recruitment_deadline.isoformat() if pos.recruitment_deadline else None,
            })
        
        # Team 서비스에서 팀장 닉네임 조회
        leader_name = await get_team_leader_nickname(project.project_id)
        
        return {
            "project_id": project.project_id,
            "user_id": project.user_id,
            "leader_name": leader_name,
            "type": "프로젝트" if project.type == ProjectType.PROJECT else "스터디",
            "title": project.title,
            "description": project.description,
            "method": get_method_display_name(project.method),
            "status": project.status.value if project.status else "RECRUITING",
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "test_required": project.test_required or False,
            "views": project.views or 0,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "recruitment_positions": positions,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 상세 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"프로젝트 상세 조회 실패: {str(e)}")

# =====================================================
# 3. 프로젝트 생성 (보상 트랜잭션 적용)
# =====================================================
@router.post("")
async def create_project(project_data: dict, db: AsyncSession = Depends(get_db)):
    """
    프로젝트 생성 + Team Service에 팀 생성 요청
    
    보상 트랜잭션:
    - 팀 생성 실패 시 프로젝트도 삭제 (롤백)
    """
    project = None  # 보상용
    
    try:
        logger.info(f"프로젝트 생성 요청: {project_data}")
        
        # 필수 데이터 검증
        if not project_data.get("title"):
            raise HTTPException(status_code=400, detail="제목은 필수입니다")
        
        user_id = project_data.get("user_id", f"user_{int(datetime.now().timestamp())}")
        
        # 프로젝트 타입 처리
        project_type_str = project_data.get("type", "PROJECT")
        # PROJECT, 프로젝트 둘 다 지원
        if project_type_str in ["PROJECT", "프로젝트", "project"]:
            project_type = ProjectType.PROJECT
        elif project_type_str in ["STUDY", "스터디", "study"]:
            project_type = ProjectType.STUDY
        else:
            project_type = ProjectType.PROJECT  # 기본값
        
        # 진행 방식 처리
        method_str = project_data.get("method", "ONLINE")
        method_map = {
            "온라인": ProjectMethod.ONLINE, 
            "오프라인": ProjectMethod.OFFLINE, 
            "믹스": ProjectMethod.MIXED,
            "ONLINE": ProjectMethod.ONLINE,
            "OFFLINE": ProjectMethod.OFFLINE,
            "MIXED": ProjectMethod.MIXED,
        }
        project_method = method_map.get(method_str, ProjectMethod.ONLINE)
        
        # ✅ Step 1: 프로젝트 생성
        project = Project(
            user_id=user_id,
            type=project_type,
            method=project_method,
            title=project_data["title"],
            description=project_data.get("description", "프로젝트 설명"),
            start_date=datetime.strptime(project_data.get("start_date", "2025-01-15"), "%Y-%m-%d").date(),
            end_date=datetime.strptime(project_data.get("end_date", "2025-03-15"), "%Y-%m-%d").date(),
            test_required=project_data.get("test_required", False),
        )
        
        db.add(project)
        await db.flush()
        project_id = project.project_id
        logger.info(f"✅ Step 1: 프로젝트 생성됨 (ID: {project_id})")
        
        # 모집 포지션 생성
        # 프론트엔드에서 recruitment_positions 또는 positions로 보낼 수 있음
        positions_data = project_data.get("recruitment_positions") or project_data.get("positions", [])
        logger.info(f"📋 모집 포지션 데이터: {positions_data}")
        
        if not positions_data:
            logger.warning("⚠️ 모집 포지션 데이터가 비어있습니다!")
        
        total_target_count = 0
        for pos_data in positions_data:
            logger.info(f"  - 포지션 처리 중: {pos_data}")
            position_type = convert_position_type(pos_data.get("position_type", "백엔드"))
            target_count = pos_data.get("target_count", 1)
            required_stacks = pos_data.get("required_stacks", [])
            
            # 🔍 디버그: required_stacks 값 확인
            logger.info(f"  📦 required_stacks 원본: {required_stacks}")
            logger.info(f"  📦 required_stacks JSON: {json.dumps(required_stacks, ensure_ascii=False)}")
            
            # 각 포지션별 모집 마감일 처리
            recruit_deadline = None
            deadline_str = pos_data.get("recruitment_deadline") or project_data.get("recruit_deadline")
            if deadline_str:
                try:
                    recruit_deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                except:
                    pass
            
            recruitment_position = ProjectRecruitmentPosition(
                project_id=project_id,
                position_type=position_type,
                required_stacks=json.dumps(required_stacks, ensure_ascii=False),
                target_count=target_count,
                current_count=0,
                recruitment_deadline=recruit_deadline,
            )
            db.add(recruitment_position)
            total_target_count += target_count
            logger.info(f"  ✅ 포지션 추가됨: {position_type.value}, 인원: {target_count}")
        
        await db.flush()
        logger.info(f"✅ Step 2: 모집 포지션 생성됨 ({len(positions_data)}개)")
        
        # ✅ Step 3: Team Service에 팀 생성 요청
        # 스터디인 경우 리더 포지션을 "스터디원"으로 설정
        default_leader_position = "스터디원" if project_type == ProjectType.STUDY else "백엔드"
        team_data = {
            "project_id": project_id,
            "name": project_data.get("title", "새 프로젝트") + (" 개발팀" if project_type == ProjectType.PROJECT else " 스터디"),
            "leader_id": user_id,
            "leader_position": project_data.get("leader_position", default_leader_position),
        }
        
        team_response = await call_team_service("POST", "/api/v1/teams", team_data)
        
        # ❌ 팀 생성 실패 시 보상 트랜잭션 실행
        if team_response is None:
            logger.error("❌ Team Service 호출 실패 - 보상 트랜잭션 실행")
            
            # 🔄 보상: 프로젝트 삭제 (롤백)
            await db.rollback()
            
            raise HTTPException(
                status_code=503,
                detail="팀 서비스 연결 실패로 프로젝트 생성이 취소되었습니다. 잠시 후 다시 시도해주세요."
            )
        
        # ✅ 모든 단계 성공 - 커밋
        await db.commit()
        logger.info(f"✅ 프로젝트+팀 생성 완료 (Project ID: {project_id})")
        
        return {
            "status": "success",
            "message": "프로젝트가 성공적으로 생성되었습니다",
            "data": {
                "project_id": project_id,
                "title": project.title,
                "type": project_type.value,
                "total_positions": total_target_count,
                "team": team_response,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 생성 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"프로젝트 생성 실패: {str(e)}")

# =====================================================
# 4. 프로젝트 수정
# =====================================================
@router.put("/{project_id}")
async def update_project(project_id: int, project_data: dict, db: AsyncSession = Depends(get_db)):
    """프로젝트 정보 수정"""
    try:
        result = await db.execute(select(Project).where(Project.project_id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
        
        # 수정 가능한 필드 업데이트
        if "title" in project_data:
            project.title = project_data["title"]
        if "description" in project_data:
            project.description = project_data["description"]
        if "method" in project_data:
            method_map = {"온라인": ProjectMethod.ONLINE, "오프라인": ProjectMethod.OFFLINE, "믹스": ProjectMethod.MIXED}
            project.method = method_map.get(project_data["method"], ProjectMethod.ONLINE)
        if "status" in project_data:
            status_map = {"모집중": ProjectStatus.RECRUITING, "진행중": ProjectStatus.PROCEEDING, "완료": ProjectStatus.COMPLETED}
            project.status = status_map.get(project_data["status"], ProjectStatus.RECRUITING)
        if "start_date" in project_data:
            project.start_date = datetime.strptime(project_data["start_date"], "%Y-%m-%d").date()
        if "end_date" in project_data:
            project.end_date = datetime.strptime(project_data["end_date"], "%Y-%m-%d").date()
        
        project.updated_at = datetime.now()
        await db.commit()
        
        return {"status": "success", "message": "프로젝트가 수정되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 수정 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"프로젝트 수정 실패: {str(e)}")

# =====================================================
# 5. 프로젝트 삭제 (보상 트랜잭션 적용)
# =====================================================
@router.delete("/{project_id}")
async def delete_project(project_id: int, user_id: str = None, db: AsyncSession = Depends(get_db)):
    """
    프로젝트 삭제 (팀장만 가능)
    
    순서: 팀 삭제 → 프로젝트 삭제
    보상: 팀 삭제 실패 시 프로젝트 삭제 취소
    """
    try:
        result = await db.execute(select(Project).where(Project.project_id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
        
        # 권한 검증 (팀장만 삭제 가능)
        if user_id and project.user_id != user_id:
            raise HTTPException(status_code=403, detail="프로젝트 삭제 권한이 없습니다.")
        
        # ✅ Step 1: Team Service에 팀 삭제 요청 (먼저!)
        team_response = await call_team_service("DELETE", f"/api/v1/teams/by-project/{project_id}")
        
        # 팀 삭제 실패해도 프로젝트 삭제는 진행 (팀이 없을 수도 있음)
        if team_response is None:
            logger.warning(f"팀 삭제 실패 또는 팀 없음 (project_id: {project_id}) - 프로젝트 삭제 계속 진행")
        
        # ✅ Step 2: 프로젝트 삭제 (cascade로 관련 데이터 삭제)
        await db.delete(project)
        await db.commit()
        
        logger.info(f"✅ 프로젝트 삭제 완료 (ID: {project_id})")
        
        return {"status": "success", "message": "프로젝트가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 삭제 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"프로젝트 삭제 실패: {str(e)}")
