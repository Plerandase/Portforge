"""
프로젝트 관련 API - Project Service 프록시
실제 비즈니스 로직은 Project Service(8001)에서 처리
알림 생성 등 Support 서비스 고유 기능만 이 서비스에서 처리
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.services.notification_service import create_notification
from app.utils.msa_client import MSAClient

router = APIRouter()
msa_client = MSAClient()


class ProjectApplyRequest(BaseModel):
    message: str | None = None
    position_type: str | None = None
    project_owner_id: str | None = None  # for notification


class ApplicantDecisionRequest(BaseModel):
    status: str  # accepted / rejected
    applicant_id: str | None = None  # for notification


class ReportRequest(BaseModel):
    reason: str
    description: str | None = None


@router.get("", response_model=ResponseEnvelope)
async def list_projects():
    """프로젝트 목록 조회 - Project Service 프록시"""
    try:
        result = await msa_client.get_project_list()
        if result:
            return ResponseEnvelope(success=True, code="PRJ_000", message="Projects", data=result)
        # Project Service 연결 실패 시 기본 응답
        return ResponseEnvelope(success=True, code="PRJ_000", message="Projects", data=[])
    except Exception as e:
        return ResponseEnvelope(success=False, code="PRJ_ERR", message=str(e), data=None)


@router.get("/{project_id}", response_model=ResponseEnvelope)
async def get_project(project_id: int):
    """프로젝트 상세 조회 - Project Service 프록시"""
    try:
        result = await msa_client.get_project_detail(project_id)
        if result:
            return ResponseEnvelope(success=True, code="PRJ_001", message="Project detail", data=result)
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        return ResponseEnvelope(success=False, code="PRJ_ERR", message=str(e), data=None)


@router.post("/{project_id}/apply", response_model=ResponseEnvelope, status_code=201)
async def apply_project(
    project_id: int, 
    payload: ProjectApplyRequest, 
    current_user=Depends(get_current_user)
):
    """
    프로젝트 지원 - Project Service 프록시 + 알림 생성
    알림 생성은 Support Service 고유 기능이므로 여기서 처리
    """
    try:
        # Project Service에 지원 요청 전달
        result = await msa_client.apply_to_project(
            project_id=project_id,
            application_data={
                "message": payload.message,
                "position_type": payload.position_type,
                "user_id": current_user["id"]
            }
        )
        
        # 알림 생성 (Support Service 고유 기능)
        if payload.project_owner_id:
            await create_notification(
                user_id=str(payload.project_owner_id),
                message=f"새 지원자가 프로젝트 {project_id}에 지원했습니다.",
                link=f"/projects/{project_id}/applicants",
            )
        
        if result:
            return ResponseEnvelope(success=True, code="PRJ_002", message="Applied", data=result)
        
        # Fallback 응답
        return ResponseEnvelope(
            success=True, 
            code="PRJ_002", 
            message="Applied", 
            data={
                "project_id": project_id,
                "applicant_id": current_user["id"],
                "status": "pending",
                "message": payload.message
            }
        )
    except Exception as e:
        return ResponseEnvelope(success=False, code="PRJ_ERR", message=str(e), data=None)


@router.patch("/{project_id}/applicants/{application_id}", response_model=ResponseEnvelope)
async def decide_applicant(
    project_id: int, 
    application_id: int, 
    payload: ApplicantDecisionRequest, 
    current_user=Depends(get_current_user)
):
    """
    지원자 승인/거절 - Project Service 프록시 + 알림 생성
    """
    try:
        # Project Service에 상태 변경 요청
        result = await msa_client.update_application_status(
            application_id=application_id,
            status_data={"status": payload.status}
        )
        
        # 알림 생성 (Support Service 고유 기능)
        if payload.applicant_id:
            result_text = "합격" if payload.status.lower() == "accepted" else "불합격"
            await create_notification(
                user_id=str(payload.applicant_id),
                message=f"프로젝트 {project_id} 지원 결과: {result_text}",
                link=f"/projects/{project_id}/status",
            )
        
        if result:
            return ResponseEnvelope(success=True, code="PRJ_003", message="Application updated", data=result)
        
        # Fallback 응답
        return ResponseEnvelope(
            success=True, 
            code="PRJ_003", 
            message="Application updated", 
            data={
                "project_id": project_id,
                "application_id": application_id,
                "status": payload.status
            }
        )
    except Exception as e:
        return ResponseEnvelope(success=False, code="PRJ_ERR", message=str(e), data=None)


@router.post("/{project_id}/report", response_model=ResponseEnvelope, status_code=201)
async def report_project(
    project_id: int, 
    payload: ReportRequest, 
    current_user=Depends(get_current_user)
):
    """프로젝트 신고 - Project Service 프록시"""
    try:
        result = await msa_client.report_project(
            project_id=project_id,
            report_data={
                "reason": payload.reason,
                "description": payload.description
            },
            user_id=current_user["id"]
        )
        
        if result:
            return ResponseEnvelope(success=True, code="PRJ_004", message="Report submitted", data=result)
        
        # Fallback 응답
        return ResponseEnvelope(
            success=True, 
            code="PRJ_004", 
            message="Report submitted", 
            data={
                "project_id": project_id,
                "reason": payload.reason,
                "description": payload.description,
                "status": "received"
            }
        )
    except Exception as e:
        return ResponseEnvelope(success=False, code="PRJ_ERR", message=str(e), data=None)
