from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class ProjectType(str, Enum):
    PROJECT = "PROJECT"
    STUDY = "STUDY"

class ProjectMethod(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MIXED = "MIXED"

class ProjectStatus(str, Enum):
    RECRUITING = "RECRUITING"
    PROCEEDING = "PROCEEDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"

class PositionType(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DB = "DB"
    INFRA = "INFRA"
    DESIGN = "DESIGN"
    ETC = "ETC"
    STUDY_MEMBER = "STUDY_MEMBER"

class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RecruitmentPositionResponse(BaseModel):
    """모집 포지션 응답"""
    position_type: str
    required_stacks: Optional[List[str]] = []
    target_count: Optional[int] = 0
    current_count: int = 0
    recruitment_deadline: Optional[date] = None  # 모집 마감일 추가

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    project_id: int
    title: str
    description: str
    status: ProjectStatus
    start_date: date
    end_date: date

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    user_id: str
    type: ProjectType
    method: ProjectMethod
    test_required: bool
    views: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    recruitment_positions: Optional[List[RecruitmentPositionResponse]] = []
    author_name: Optional[str] = None  # Auth 서비스에서 조회
    leader_name: Optional[str] = None  # Team 서비스에서 조회

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    application_id: int
    project_id: int
    user_id: str
    position_type: PositionType
    message: Optional[str] = None
    status: ApplicationStatus
    created_at: datetime

    class Config:
        from_attributes = True