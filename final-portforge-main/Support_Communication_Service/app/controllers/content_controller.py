from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.schemas.base import ResponseEnvelope
from app.services.notice_service import list_notices, create_notice as create_notice_service
from app.services.banner_service import list_banners as get_banners
from app.services import report_service
from app.core.deps import get_current_user

router = APIRouter()


class NoticeCreateRequest(BaseModel):
    title: str
    content: str


class BannerCreateRequest(BaseModel):
    title: str
    link: str
    is_active: Optional[bool] = True


class ReportCreateRequest(BaseModel):
    project_id: Optional[int] = None
    type: str = "REPORT"
    content: str


@router.get("/notices", response_model=ResponseEnvelope)
async def get_notices():
    """공지사항 목록 조회"""
    notices = await list_notices(limit=20)
    return ResponseEnvelope(success=True, code="CNT_000", message="Notices list", data=notices)


@router.post("/notices", response_model=ResponseEnvelope, status_code=201)
async def create_notice(payload: NoticeCreateRequest, current_user=Depends(get_current_user)):
    """공지사항 생성 (관리자 전용)"""
    notice = await create_notice_service(title=payload.title, content=payload.content)
    return ResponseEnvelope(success=True, code="CNT_002", message="Notice created", data=notice)


@router.get("/notices/latest", response_model=ResponseEnvelope)
async def get_latest_notice():
    """최신 공지사항 조회"""
    notices = await list_notices(limit=1)
    latest = notices[0] if notices else None
    return ResponseEnvelope(success=True, code="CNT_000", message="Latest notice", data=latest)


@router.get("/banners", response_model=ResponseEnvelope)
async def list_banners():
    """?? ?? ??"""
    try:
        banners = await get_banners()
        return ResponseEnvelope(success=True, code="CNT_001", message="Banners", data=banners)
    except Exception:
        # ??? ?? ? ?? ?? ??
        banners = [
            {"id": 1, "title": "AI ???", "image": "https://cdn.example.com/banner1.png", "link": "https://example.com/event/1"}
        ]
        return ResponseEnvelope(success=True, code="CNT_001", message="Banners", data=banners)

@router.post("/support/reports", response_model=ResponseEnvelope, status_code=201)
async def create_report(payload: ReportCreateRequest, current_user=Depends(get_current_user)):
    """Create a report/inquiry/bug entry."""
    report_type = (payload.type or "REPORT").upper()
    if report_type not in {"REPORT", "INQUIRY", "BUG"}:
        report_type = "REPORT"
    report = await report_service.create_report(
        user_id=current_user["id"],
        project_id=payload.project_id or 0,
        content=payload.content,
        type=report_type,
    )
    return ResponseEnvelope(success=True, code="CNT_003", message="Report created", data=report)
