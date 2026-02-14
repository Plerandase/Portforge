from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationOut(BaseModel):
    notification_id: int
    user_id: str
    message: Optional[str] = None
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NoticeCreate(BaseModel):
    title: str
    content: str


class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoticeOut(BaseModel):
    notice_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class BannerOut(BaseModel):
    banner_id: int
    title: Optional[str] = None
    link: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class BannerCreate(BaseModel):
    title: str
    link: Optional[str] = None
    is_active: bool = True


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectReportOut(BaseModel):
    report_id: int
    user_id: str
    project_id: int
    type: str
    content: str
    status: str
    resolution_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class EventCreate(BaseModel):
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    image_url: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    image_url: Optional[str] = None


class EventOut(BaseModel):
    event_id: int
    title: Optional[str] = None
    category: Optional[str] = None
    event_description: Optional[str] = None
    image_url: Optional[str] = None
    event_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReportDecisionRequest(BaseModel):
    action: str  # warn | dismiss | delete
    note: Optional[str] = None
