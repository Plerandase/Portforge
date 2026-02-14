"""
Project Service - 지원서 (Applications) API (보상 트랜잭션 + Circuit Breaker 적용)
ERD 기반 MSA 분리: 지원서 CRUD 및 승인/거절 처리
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import logging
import httpx
import time
import json

from app.core.database import get_db
from app.models.project_recruitment import (
    Project, ProjectRecruitmentPosition, Application,
    ApplicationStatus, PositionType as StackCategory  # Alias for compatibility
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["applications"])

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

# =====================================================
# Team Service 통신용 클라이언트 (Circuit Breaker 적용)
# =====================================================
import os
TEAM_SERVICE_URL = os.getenv("TEAM_SERVICE_URL", "http://team-service")
SUPPORT_SERVICE_URL = os.getenv("SUPPORT_SERVICE_URL", "http://support-service")

async def call_team_service(method: str, endpoint: str, data: dict = None) -> dict:
    """Team Service API 호출 (Circuit Breaker 적용)"""
    
    if not team_service_breaker.can_execute():
        logger.warning("Team Service 호출 차단됨 (Circuit Open)")
        return None
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{TEAM_SERVICE_URL}{endpoint}"
        try:
            if method == "POST":
                response = await client.post(url, json=data)
            elif method == "GET":
                response = await client.get(url)
            else:
                response = await client.request(method, url, json=data)
            
            if response.status_code >= 400:
                logger.error(f"Team Service 호출 실패: {response.status_code}")
                team_service_breaker.record_failure()
                return None
            
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
    """Support Service에 알림 전송 (실패해도 계속 진행 - Fire and Forget)"""
    if not support_service_breaker.can_execute():
        logger.debug("알림 전송 스킵 (Support Service Circuit Open)")
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
# 1. 프로젝트 지원하기
# =====================================================
@router.post("/{project_id}/applications")
async def apply_to_project(
    project_id: int,
    application_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """프로젝트에 지원하기"""
    try:
        # 프로젝트 존재 확인
        project_result = await db.execute(select(Project).where(Project.project_id == project_id))
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
        
        user_id = application_data.get("user_id")
        position_type_str = application_data.get("position_type", "백엔드")
        message = application_data.get("message", "")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # 이미 지원했는지 확인
        existing_result = await db.execute(
            select(Application).where(
                Application.project_id == project_id,
                Application.user_id == user_id
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            existing_status = existing.status.value if existing.status else "PENDING"
            raise HTTPException(
                status_code=409,
                detail=f"Already applied to this project (status: {existing_status})"
            )
        
        # 포지션 타입 변환
        position_map = {
            "프론트엔드": StackCategory.FRONTEND,
            "백엔드": StackCategory.BACKEND,
            "디자인": StackCategory.DESIGN,
            "DB": StackCategory.DB,
            "인프라": StackCategory.INFRA,
            "기타": StackCategory.ETC,
            "스터디원": StackCategory.STUDY_MEMBER,
        }
        position_type = position_map.get(position_type_str, StackCategory.ETC)
        
        # 지원서 생성
        new_application = Application(
            project_id=project_id,
            user_id=user_id,
            position_type=position_type,
            message=message,
            status=ApplicationStatus.PENDING,
        )
        
        db.add(new_application)
        await db.commit()
        await db.refresh(new_application)
        
        # 팀장에게 알림 전송 (실패해도 계속)
        await send_notification(
            project.user_id,
            f"'{project.title}' 프로젝트에 새로운 지원자가 있습니다!",
            f"/projects/{project_id}"
        )
        
        logger.info(f"✅ 지원서 생성 완료: 사용자 {user_id} -> 프로젝트 {project_id}")
        
        return {
            "status": "success",
            "message": "지원이 완료되었습니다.",
            "data": {
                "application_id": new_application.application_id,
                "project_id": project_id,
                "user_id": user_id,
                "position_type": position_type_str,
                "status": "PENDING",
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지원서 생성 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"지원 실패: {str(e)}")

# =====================================================
# 2. 프로젝트 지원자 목록 조회
# =====================================================
@router.get("/{project_id}/applications")
async def get_project_applications(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트의 지원자 목록 조회 (팀장용)"""
    try:
        applications_result = await db.execute(
            select(Application)
            .where(Application.project_id == project_id)
            .order_by(Application.created_at.desc())
        )
        applications = applications_result.scalars().all()
        
        application_list = []
        for app in applications:
            position_clean = app.position_type.value if app.position_type else "UNKNOWN"
            status_clean = app.status.value if app.status else "PENDING"
            
            application_list.append({
                "application_id": app.application_id,
                "user_id": app.user_id,
                "position_type": position_clean,
                "message": app.message,
                "status": status_clean,
                "created_at": app.created_at.isoformat() if app.created_at else None,
            })
        
        return {
            "status": "success",
            "data": {
                "project_id": project_id,
                "applications": application_list,
            }
        }
        
    except Exception as e:
        logger.error(f"지원자 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"지원자 목록 조회 실패: {str(e)}")

# =====================================================
# 3. 지원자 승인/거절 (보상 트랜잭션 적용)
# =====================================================
@router.patch("/{project_id}/applications/{application_id}")
async def handle_application(
    project_id: int,
    application_id: int,
    action_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    지원자 승인/거절 처리
    
    보상 트랜잭션 (승인 시):
    - 팀 멤버 추가 실패 시 승인 취소 (PENDING으로 복원)
    """
    try:
        action = action_data.get("status", "").lower()
        
        if action not in ["accepted", "rejected"]:
            raise HTTPException(status_code=400, detail="status는 'accepted' 또는 'rejected'만 가능합니다.")
        
        # 지원서 조회
        application_result = await db.execute(
            select(Application).where(Application.application_id == application_id)
        )
        application = application_result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(status_code=404, detail="지원서를 찾을 수 없습니다.")
        
        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(status_code=400, detail="이미 처리된 지원서입니다.")
        
        # 프로젝트 정보 조회
        project_result = await db.execute(select(Project).where(Project.project_id == project_id))
        project = project_result.scalar_one_or_none()
        
        if action == "accepted":
            # ✅ Step 1: 지원서 승인
            original_status = application.status
            application.status = ApplicationStatus.ACCEPTED
            
            # 모집 포지션 현재 인원 증가
            logger.info(f"🔍 지원서 position_type: {application.position_type}, project_id: {project_id}")
            
            position_result = await db.execute(
                select(ProjectRecruitmentPosition).where(
                    ProjectRecruitmentPosition.project_id == project_id,
                    ProjectRecruitmentPosition.position_type == application.position_type
                )
            )
            position = position_result.scalar_one_or_none()
            
            logger.info(f"🔍 매칭된 포지션: {position}")
            
            original_count = None
            if position:
                original_count = position.current_count
                position.current_count = (position.current_count or 0) + 1
                logger.info(f"✅ current_count 증가: {original_count} -> {position.current_count}")
            else:
                logger.warning(f"⚠️ 매칭되는 포지션을 찾을 수 없음! position_type={application.position_type}")
            
            await db.flush()
            logger.info(f"✅ Step 1: 지원서 승인됨 (ID: {application_id})")
            
            # ✅ Step 2: Team Service에 팀 멤버 추가 요청
            member_data = {
                "project_id": project_id,
                "user_id": application.user_id,
                "position_type": application.position_type.value if application.position_type else "BACKEND",
                "role": "MEMBER",
            }
            
            team_response = await call_team_service("POST", "/api/v1/teams/members", member_data)
            
            # ❌ 팀 멤버 추가 실패 시 보상 트랜잭션
            if team_response is None:
                logger.error("❌ Team Service 호출 실패 - 보상 트랜잭션 실행")
                
                # 🔄 보상: 승인 취소 (PENDING으로 복원)
                application.status = original_status
                if position and original_count is not None:
                    position.current_count = original_count
                
                await db.commit()  # 보상 결과 저장
                
                raise HTTPException(
                    status_code=503,
                    detail="팀 서비스 연결 실패로 승인이 취소되었습니다. 잠시 후 다시 시도해주세요."
                )
            
            # ✅ 모든 단계 성공 - 커밋
            await db.commit()
            logger.info(f"✅ 지원자 승인 완료: {application.user_id} -> 프로젝트 {project_id}")
            
            # 지원자에게 알림 (실패해도 계속)
            if project:
                await send_notification(
                    application.user_id,
                    f"'{project.title}' 프로젝트 지원이 승인되었습니다! 팀 스페이스에 참여하세요.",
                    f"/projects/{project_id}"
                )
            
            return {
                "status": "success",
                "message": "지원자가 승인되어 팀 멤버로 추가되었습니다.",
                "data": {
                    "application_id": application_id,
                    "user_id": application.user_id,
                    "team_member_added": True,
                }
            }
        
        else:  # rejected
            application.status = ApplicationStatus.REJECTED
            await db.commit()
            
            # 지원자에게 알림 (실패해도 계속)
            if project:
                await send_notification(
                    application.user_id,
                    f"'{project.title}' 프로젝트 지원이 거절되었습니다.",
                    f"/projects/{project_id}"
                )
            
            logger.info(f"✅ 지원자 거절 완료: {application.user_id}")
            
            return {
                "status": "success",
                "message": "지원자가 거절되었습니다.",
                "data": {
                    "application_id": application_id,
                    "user_id": application.user_id,
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지원 처리 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"지원 처리 실패: {str(e)}")

# =====================================================
# 4. 사용자의 지원 현황 조회
# =====================================================
@router.get("/user/{user_id}/applications")
async def get_user_applications(user_id: str, db: AsyncSession = Depends(get_db)):
    """특정 사용자의 지원 현황 조회"""
    try:
        applications_result = await db.execute(
            select(Application, Project)
            .join(Project, Application.project_id == Project.project_id)
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
        )
        applications = applications_result.all()
        
        application_list = []
        for app, project in applications:
            application_list.append({
                "application_id": app.application_id,
                "project_id": app.project_id,
                "project_title": project.title,
                "position_type": app.position_type.value if app.position_type else "UNKNOWN",
                "message": app.message,
                "status": app.status.value if app.status else "PENDING",
                "created_at": app.created_at.isoformat() if app.created_at else None,
            })
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "applications": application_list,
            }
        }
        
    except Exception as e:
        logger.error(f"사용자 지원 현황 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 지원 현황 조회 실패: {str(e)}")

# =====================================================
# 5. 모집 포지션 조회 (지원하기 페이지용)
# =====================================================
@router.get("/{project_id}/positions")
async def get_project_positions(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트의 모집 포지션 목록 조회"""
    try:
        positions_result = await db.execute(
            select(ProjectRecruitmentPosition)
            .where(ProjectRecruitmentPosition.project_id == project_id)
        )
        positions = positions_result.scalars().all()
        
        position_list = []
        for pos in positions:
            position_name_map = {
                "FRONTEND": "프론트엔드",
                "BACKEND": "백엔드",
                "DESIGN": "디자인",
                "DB": "DB",
                "INFRA": "인프라",
                "ETC": "기타",
                "STUDY_MEMBER": "스터디원",
            }
            position_type = pos.position_type.value if pos.position_type else "ETC"
            
            # required_stacks 파싱
            stacks = []
            if pos.required_stacks:
                try:
                    stacks = json.loads(pos.required_stacks) if isinstance(pos.required_stacks, str) else []
                except:
                    pass
            
            position_list.append({
                "position_type": position_type,
                "position_name": position_name_map.get(position_type, position_type),
                "required_stacks": stacks,
                "target_count": pos.target_count or 0,
                "current_count": pos.current_count or 0,
                "is_available": (pos.current_count or 0) < (pos.target_count or 0),
                "recruitment_deadline": pos.recruitment_deadline.isoformat() if pos.recruitment_deadline else None,
            })
        
        return {
            "status": "success",
            "data": {
                "project_id": project_id,
                "positions": position_list,
            }
        }
        
    except Exception as e:
        logger.error(f"모집 포지션 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"모집 포지션 조회 실패: {str(e)}")

# =====================================================
# 6. 지원서 상세 조회 (누락 기능 추가)
# =====================================================
@router.get("/applications/{application_id}")
async def get_application_detail(application_id: int, db: AsyncSession = Depends(get_db)):
    """지원서 상세 조회"""
    try:
        query = select(Application).where(Application.application_id == application_id)
        result = await db.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
             raise HTTPException(status_code=404, detail="지원서를 찾을 수 없습니다.")
             
        return {
            "status": "success",
            "data": {
                "application_id": app.application_id,
                "project_id": app.project_id,
                "user_id": app.user_id,
                "position_type": app.position_type.value if app.position_type else "UNKNOWN",
                "message": app.message,
                "status": app.status.value if app.status else "PENDING",
                "created_at": app.created_at.isoformat() if app.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지원서 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="오류 발생")

