from fastapi import APIRouter, Depends
from typing import Optional
from pydantic import BaseModel

from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.services.notification_service import list_notifications, create_notification, mark_notifications_read

router = APIRouter()


class NotificationCreate(BaseModel):
    user_id: str
    message: str
    link: Optional[str] = None


@router.get("", response_model=ResponseEnvelope)
async def list_notifications_api(user_id: Optional[str] = None, current_user=Depends(get_current_user)):
    data = await list_notifications(user_id or str(current_user.get("id")))
    return ResponseEnvelope(success=True, code="NOTI_000", message="Notifications", data=data)


@router.post("", response_model=ResponseEnvelope)
async def create_notification_api(notification: NotificationCreate):
    """알림 생성 API (다른 서비스에서 호출)"""
    data = await create_notification(
        user_id=notification.user_id,
        message=notification.message,
        link=notification.link
    )
    return ResponseEnvelope(success=True, code="NOTI_001", message="Notification created", data=data)


@router.post("/read", response_model=ResponseEnvelope)
async def mark_notifications_read_api(user_id: str):
    """사용자의 모든 알림을 읽음 처리"""
    count = await mark_notifications_read(user_id)
    return ResponseEnvelope(success=True, code="NOTI_002", message=f"{count} notifications marked as read", data={"count": count})

