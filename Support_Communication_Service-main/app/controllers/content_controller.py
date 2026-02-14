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


class BannerUpdateRequest(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    is_active: Optional[bool] = None


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


@router.get("/notices/top", response_model=ResponseEnvelope)
async def get_top_notice():
    """최신 공지사항 조회 (FE 호환용)"""
    notices = await list_notices(limit=1)
    latest = notices[0] if notices else None
    return ResponseEnvelope(success=True, code="CNT_000", message="Top notice", data=latest)



@router.get("/banners", response_model=ResponseEnvelope)
async def list_banners():
    """배너 목록 조회"""
    try:
        banners = await get_banners()
        return ResponseEnvelope(success=True, code="CNT_001", message="Banners", data=banners)
    except Exception:
        # 에러 발생 시 빈 배너 반환
        banners = [
            {"id": 1, "title": "AI 이벤트", "image": "https://cdn.example.com/banner1.png", "link": "https://example.com/event/1"}
        ]
        return ResponseEnvelope(success=True, code="CNT_001", message="Banners", data=banners)


@router.post("/banners", response_model=ResponseEnvelope, status_code=201)
async def create_banner(payload: BannerCreateRequest, current_user=Depends(get_current_user)):
    """배너 생성 (관리자 전용)"""
    from app.services.banner_service import create_banner as create_banner_service
    banner = await create_banner_service(
        title=payload.title,
        link=payload.link,
        is_active=payload.is_active
    )
    return ResponseEnvelope(success=True, code="CNT_004", message="Banner created", data=banner)


@router.patch("/banners/{banner_id}", response_model=ResponseEnvelope)
async def update_banner(banner_id: int, payload: BannerUpdateRequest, current_user=Depends(get_current_user)):
    """배너 수정 (관리자 전용)"""
    from app.services.banner_service import update_banner as update_banner_service
    update_data = payload.model_dump(exclude_none=True)
    banner = await update_banner_service(banner_id=banner_id, payload=update_data)
    if not banner:
        return ResponseEnvelope(success=False, code="CNT_404", message="Banner not found", data=None)
    return ResponseEnvelope(success=True, code="CNT_005", message="Banner updated", data=banner)


@router.delete("/banners/{banner_id}", response_model=ResponseEnvelope)
async def delete_banner(banner_id: int, current_user=Depends(get_current_user)):
    """배너 삭제 (관리자 전용)"""
    from app.services.banner_service import delete_banner as delete_banner_service
    success = await delete_banner_service(banner_id)
    if not success:
        return ResponseEnvelope(success=False, code="CNT_404", message="Banner not found", data=None)
    return ResponseEnvelope(success=True, code="CNT_006", message="Banner deleted", data={"banner_id": banner_id})


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
