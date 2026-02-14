from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.services import notice_service, report_service, banner_service, notification_service
from app.utils.msa_client import msa_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReportDecisionRequest(BaseModel):
    action: str  # warn | dismiss | delete
    note: str | None = None


class NoticeCreateRequest(BaseModel):
    title: str
    content: str


class NoticeUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


class BannerCreateRequest(BaseModel):
    title: str
    link: str | None = None
    is_active: bool = True


class BannerUpdateRequest(BaseModel):
    title: str | None = None
    link: str | None = None
    is_active: bool | None = None


@router.get("", response_model=ResponseEnvelope)
async def list_all_projects(current_user=Depends(get_current_user)):
    projects = [{"id": 1, "author_id": 10, "title": "Project A"}]
    return ResponseEnvelope(success=True, code="ADM_000", message="All projects", data=projects)


@router.delete("/projects/{project_id}", response_model=ResponseEnvelope)
async def delete_project(project_id: int, current_user=Depends(get_current_user)):
    """관리자가 프로젝트 삭제"""
    try:
        # Project Service에 삭제 요청
        project_info = await msa_client.get_project_basic(project_id)
        if not project_info or not project_info.get("data"):
            return ResponseEnvelope(success=False, code="ADM_404", message="Project not found", data=None)
        
        # Project Service DELETE API 호출
        delete_response = await msa_client._make_request("project", f"/projects/{project_id}", "DELETE")
        
        if delete_response:
            logger.info(f"프로젝트 {project_id} 삭제 완료")
            return ResponseEnvelope(success=True, code="ADM_001", message="Project removed", data={"project_id": project_id})
        else:
            logger.error(f"프로젝트 {project_id} 삭제 실패")
            return ResponseEnvelope(success=False, code="ADM_500", message="Project deletion failed", data=None)
    except Exception as e:
        logger.error(f"프로젝트 삭제 중 오류: {str(e)}")
        return ResponseEnvelope(success=False, code="ADM_500", message=f"Error: {str(e)}", data=None)


@router.get("/reports", response_model=ResponseEnvelope)
async def list_reports(current_user=Depends(get_current_user)):
    reports = await report_service.list_reports()
    return ResponseEnvelope(success=True, code="ADM_002", message="Reports", data=reports)


@router.patch("/reports/{report_id}", response_model=ResponseEnvelope)
async def handle_report(report_id: int, payload: ReportDecisionRequest, current_user=Depends(get_current_user)):
    logger.info(f"=== 신고 처리 시작: report_id={report_id}, action={payload.action} ===")
    
    updated = await report_service.update_report(report_id=report_id, action=payload.action, note=payload.note)
    if not updated:
        logger.error(f"신고 {report_id} 를 찾을 수 없음")
        return ResponseEnvelope(success=False, code="ADM_404", message="Report not found", data=None)
    
    reporter_id = updated.get("user_id")
    project_id = updated.get("project_id")
    action = payload.action.lower()
    
    logger.info(f"신고 정보: reporter_id={reporter_id}, project_id={project_id}, action={action}")
    
    # 1. 프로젝트 삭제 전에 팀장 정보 먼저 조회 (삭제 후에는 조회 불가)
    leader_id = None
    if project_id:
        try:
            logger.info(f"프로젝트 {project_id} 정보 조회 시작")
            project_info = await msa_client.get_project_basic(project_id)
            logger.info(f"프로젝트 정보 응답: {project_info}")
            
            if project_info and project_info.get("data"):
                project_data = project_info["data"]
                team_id = project_data.get("team_id")
                logger.info(f"team_id: {team_id}")
                
                if team_id:
                    team_members_response = await msa_client.get_team_members(team_id)
                    logger.info(f"팀 멤버 응답: {team_members_response}")
                    
                    if team_members_response and team_members_response.get("data"):
                        members = team_members_response["data"]
                        leader = next((m for m in members if m.get("role") == "LEADER"), None)
                        if leader:
                            leader_id = leader.get("user_id")
                            logger.info(f"✅ 팀장 정보 조회 완료: {leader_id}")
                        else:
                            logger.warning(f"팀장을 찾을 수 없음. 멤버 목록: {members}")
                    else:
                        logger.warning(f"팀 멤버 데이터 없음")
                else:
                    logger.warning(f"team_id가 없음")
            else:
                logger.warning(f"프로젝트 정보 없음")
        except Exception as e:
            logger.error(f"❌ 팀장 정보 조회 실패: {str(e)}", exc_info=True)
    
    # 2. action="delete"이면 실제로 프로젝트 삭제
    if action == "delete" and project_id:
        try:
            logger.info(f"프로젝트 {project_id} 삭제 시작")
            delete_response = await msa_client._make_request("project", f"/projects/{project_id}", "DELETE")
            if delete_response:
                logger.info(f"✅ 신고 처리: 프로젝트 {project_id} 삭제 완료")
            else:
                logger.error(f"❌ 신고 처리: 프로젝트 {project_id} 삭제 실패 (응답 없음)")
        except Exception as e:
            logger.error(f"❌ 신고 처리 중 프로젝트 삭제 오류: {str(e)}", exc_info=True)
    
    # 3. 알림 전송: 신고자와 프로젝트 팀장에게
    try:
        logger.info(f"알림 전송 시작: reporter_id={reporter_id}, leader_id={leader_id}")
        
        # 알림 메시지 생성
        if action == "delete":
            message = f"신고하신 프로젝트(ID: {project_id})가 관리자에 의해 삭제되었습니다."
            team_message = f"귀하의 프로젝트(ID: {project_id})가 신고 접수로 인해 삭제되었습니다."
        elif action == "warn":
            message = f"신고하신 프로젝트(ID: {project_id})의 작성자에게 경고 조치가 취해졌습니다."
            team_message = f"귀하의 프로젝트(ID: {project_id})에 대한 신고로 경고 조치가 취해졌습니다."
        elif action == "dismiss":
            message = f"신고하신 프로젝트(ID: {project_id})는 무혐의로 처리되었습니다."
            team_message = f"귀하의 프로젝트(ID: {project_id})에 대한 신고가 무혐의로 처리되었습니다."
        else:
            message = f"신고하신 프로젝트(ID: {project_id})가 처리되었습니다."
            team_message = f"귀하의 프로젝트(ID: {project_id})에 대한 신고가 처리되었습니다."
        
        logger.info(f"알림 메시지: reporter='{message}', team='{team_message}'")
        
        # 신고자에게 알림
        if reporter_id:
            logger.info(f"신고자 {reporter_id}에게 알림 전송 시도")
            result = await notification_service.create_notification(
                user_id=reporter_id,
                message=message,
                link=f"/projects/{project_id}"
            )
            logger.info(f"✅ 신고자({reporter_id})에게 알림 전송 완료: {result}")
        else:
            logger.warning("reporter_id가 없어 신고자 알림 전송 불가")
        
        # 팀장에게 알림 (이미 조회한 leader_id 사용)
        if leader_id and leader_id != reporter_id:
            logger.info(f"팀장 {leader_id}에게 알림 전송 시도")
            result = await notification_service.create_notification(
                user_id=leader_id,
                message=team_message,
                link=f"/projects/{project_id}"
            )
            logger.info(f"✅ 팀장({leader_id})에게 알림 전송 완료: {result}")
        elif leader_id == reporter_id:
            logger.info(f"팀장과 신고자가 동일하여 중복 알림 방지")
        else:
            logger.warning("leader_id가 없어 팀장 알림 전송 불가")
            
    except Exception as e:
        logger.error(f"❌ 알림 전송 중 오류 발생: {str(e)}", exc_info=True)
        # 알림 실패해도 신고 처리는 성공으로 반환
    
    logger.info(f"=== 신고 처리 완료: report_id={report_id} ===")
    return ResponseEnvelope(success=True, code="ADM_003", message="Report handled", data=updated)


@router.get("/banners", response_model=ResponseEnvelope)
async def list_banners(current_user=Depends(get_current_user)):
    """배너 목록 조회"""
    banners = await banner_service.list_banners()
    return ResponseEnvelope(success=True, code="ADM_004", message="Banners", data=banners)


@router.post("/banners", response_model=ResponseEnvelope, status_code=201)
async def create_banner(payload: BannerCreateRequest, current_user=Depends(get_current_user)):
    """배너 생성"""
    banner = await banner_service.create_banner(
        title=payload.title,
        link=payload.link,
        is_active=payload.is_active
    )
    return ResponseEnvelope(success=True, code="ADM_009", message="Banner created", data=banner)


@router.patch("/banners/{banner_id}", response_model=ResponseEnvelope)
async def update_banner(banner_id: int, payload: BannerUpdateRequest, current_user=Depends(get_current_user)):
    """배너 수정"""
    update_data = payload.model_dump(exclude_none=True)
    banner = await banner_service.update_banner(banner_id=banner_id, payload=update_data)
    if not banner:
        return ResponseEnvelope(success=False, code="ADM_404", message="Banner not found", data=None)
    return ResponseEnvelope(success=True, code="ADM_010", message="Banner updated", data=banner)


@router.delete("/banners/{banner_id}", response_model=ResponseEnvelope)
async def delete_banner(banner_id: int, current_user=Depends(get_current_user)):
    """배너 삭제"""
    success = await banner_service.delete_banner(banner_id)
    if not success:
        return ResponseEnvelope(success=False, code="ADM_404", message="Banner not found", data=None)
    return ResponseEnvelope(success=True, code="ADM_011", message="Banner deleted", data={"banner_id": banner_id})


@router.post("/notices", response_model=ResponseEnvelope, status_code=201)
async def create_notice(payload: NoticeCreateRequest, current_user=Depends(get_current_user)):
    notice = await notice_service.create_notice(title=payload.title, content=payload.content)
    return ResponseEnvelope(success=True, code="ADM_005", message="Notice created", data=notice)


@router.patch("/notices/{notice_id}", response_model=ResponseEnvelope)
async def update_notice(notice_id: int, payload: NoticeUpdateRequest, current_user=Depends(get_current_user)):
    notice = await notice_service.update_notice(notice_id=notice_id, title=payload.title, content=payload.content)
    return ResponseEnvelope(success=True, code="ADM_006", message="Notice updated", data=notice)


@router.delete("/notices/{notice_id}", response_model=ResponseEnvelope)
async def delete_notice(notice_id: int, current_user=Depends(get_current_user)):
    await notice_service.delete_notice(notice_id)
    return ResponseEnvelope(success=True, code="ADM_007", message="Notice deleted", data=None)


@router.get("/notices", response_model=ResponseEnvelope)
async def list_notices_admin(current_user=Depends(get_current_user)):
    notices = await notice_service.list_notices(limit=100)
    return ResponseEnvelope(success=True, code="ADM_008", message="Notices", data=notices)
