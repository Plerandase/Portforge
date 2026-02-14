from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.services import notice_service, report_service

router = APIRouter()


class ReportDecisionRequest(BaseModel):
    action: str  # warn | dismiss | delete
    note: str | None = None


class NoticeCreateRequest(BaseModel):
    title: str
    content: str


class NoticeUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


@router.get("", response_model=ResponseEnvelope)
async def list_all_projects(current_user=Depends(get_current_user)):
    projects = [{"id": 1, "author_id": 10, "title": "Project A"}]
    return ResponseEnvelope(success=True, code="ADM_000", message="All projects", data=projects)


@router.delete("/projects/{project_id}", response_model=ResponseEnvelope)
async def delete_project(project_id: int, current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="ADM_001", message="Project removed", data={"project_id": project_id})


@router.get("/reports", response_model=ResponseEnvelope)
async def list_reports(current_user=Depends(get_current_user)):
    reports = await report_service.list_reports()
    return ResponseEnvelope(success=True, code="ADM_002", message="Reports", data=reports)


@router.patch("/reports/{report_id}", response_model=ResponseEnvelope)
async def handle_report(report_id: int, payload: ReportDecisionRequest, current_user=Depends(get_current_user)):
    updated = await report_service.update_report(report_id=report_id, action=payload.action, note=payload.note)
    if not updated:
        return ResponseEnvelope(success=False, code="ADM_404", message="Report not found", data=None)
    return ResponseEnvelope(success=True, code="ADM_003", message="Report handled", data=updated)


@router.get("/banners", response_model=ResponseEnvelope)
async def list_banners(current_user=Depends(get_current_user)):
    banners = [{"id": 1, "title": "Summer Hackathon"}]
    return ResponseEnvelope(success=True, code="ADM_004", message="Banners", data=banners)


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


@router.patch("/notices/{notice_id}", response_model=ResponseEnvelope)
async def update_notice(notice_id: int, payload: NoticeUpdateRequest, current_user=Depends(get_current_user)):
    notice = {"id": notice_id, **payload.model_dump(exclude_none=True)}
    return ResponseEnvelope(success=True, code="ADM_006", message="Notice updated", data=notice)


@router.delete("/notices/{notice_id}", response_model=ResponseEnvelope)
async def delete_notice(notice_id: int, current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="ADM_007", message="Notice deleted", data={"id": notice_id})
