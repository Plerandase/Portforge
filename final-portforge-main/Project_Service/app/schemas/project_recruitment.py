from pydantic import BaseModel, Field
from typing import List, Optional
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


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TestType(str, Enum):
    PRACTICE = "PRACTICE"
    APPLICATION = "APPLICATION"


# Request Schemas
class RecruitmentPositionCreate(BaseModel):
    position_type: PositionType = Field(..., description="모집 포지션 타입")
    required_stacks: str = Field(..., min_length=1, max_length=100, description="필요한 기술 스택")
    target_count: int = Field(..., gt=0, description="모집 인원")
    employment_type: Optional[str] = Field(None, max_length=20, description="고용 형태")
    recruitment_deadline: Optional[date] = Field(None, description="모집 마감일")


class RecruitmentPositionUpdate(BaseModel):
    position_type: PositionType = Field(..., description="모집 포지션 타입")
    required_stacks: str = Field(..., min_length=1, max_length=100, description="필요한 기술 스택")
    target_count: int = Field(..., gt=0, description="모집 인원")
    employment_type: Optional[str] = Field(None, max_length=20, description="고용 형태")
    recruitment_deadline: Optional[date] = Field(None, description="모집 마감일")


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="프로젝트 제목")
    description: str = Field(..., min_length=1, description="프로젝트 설명")
    type: ProjectType = Field(..., description="프로젝트 타입")
    method: ProjectMethod = Field(ProjectMethod.ONLINE, description="진행 방식")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")
    test_required: bool = Field(False, description="AI 테스트 필수 여부")
    recruitment_positions: List[RecruitmentPositionCreate] = Field(..., min_items=1, description="모집 포지션 목록")


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="프로젝트 제목")
    description: Optional[str] = Field(None, min_length=1, description="프로젝트 설명")
    type: Optional[ProjectType] = Field(None, description="프로젝트 타입")
    method: Optional[ProjectMethod] = Field(None, description="진행 방식")
    start_date: Optional[date] = Field(None, description="시작일")
    end_date: Optional[date] = Field(None, description="종료일")
    test_required: Optional[bool] = Field(None, description="AI 테스트 필수 여부")
    recruitment_positions: Optional[List[RecruitmentPositionUpdate]] = Field(None, description="모집 포지션 목록")


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus = Field(..., description="프로젝트 상태")


class ApplicationCreate(BaseModel):
    position_type: PositionType = Field(..., description="지원 포지션")
    prefer_stacks: Optional[str] = Field(None, max_length=100, description="선호 기술 스택")
    message: str = Field(..., min_length=1, description="지원 메시지")


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus = Field(..., description="지원서 상태")


class TestResultCreate(BaseModel):
    type: TestType = Field(TestType.APPLICATION, description="테스트 타입")
    score: Optional[int] = Field(None, ge=0, le=100, description="점수")
    feedback: Optional[str] = Field(None, description="피드백")


# Response Schemas
class RecruitmentPositionResponse(BaseModel):
    project_id: int = Field(..., description="프로젝트 ID")
    position_type: PositionType = Field(..., description="포지션 타입")
    required_stacks: str = Field(..., description="필요한 기술 스택")
    employment_type: Optional[str] = Field(None, description="고용 형태")
    target_count: Optional[int] = Field(None, description="목표 인원")
    current_count: int = Field(..., description="현재 인원")
    recruitment_deadline: Optional[date] = Field(None, description="모집 마감일")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    application_id: int = Field(..., description="지원서 ID")
    project_id: int = Field(..., description="프로젝트 ID")
    user_id: str = Field(..., description="지원자 ID (UUID)")
    position_type: PositionType = Field(..., description="지원 포지션")
    prefer_stacks: Optional[str] = Field(None, description="선호 기술 스택")
    message: str = Field(..., description="지원 메시지")
    status: ApplicationStatus = Field(..., description="지원서 상태")
    created_at: datetime = Field(..., description="지원일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    result_id: int = Field(..., description="결과 ID")
    user_id: str = Field(..., description="사용자 ID (UUID)")
    project_id: Optional[int] = Field(None, description="프로젝트 ID")
    application_id: Optional[int] = Field(None, description="지원서 ID")
    type: TestType = Field(..., description="테스트 타입")
    score: Optional[int] = Field(None, description="점수")
    feedback: Optional[str] = Field(None, description="피드백")
    created_at: datetime = Field(..., description="생성일시")

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    id: int = Field(..., description="프로젝트 ID")
    title: str = Field(..., description="프로젝트 제목")
    description: str = Field(..., description="프로젝트 설명")
    type: ProjectType = Field(..., description="프로젝트 타입")
    method: ProjectMethod = Field(..., description="진행 방식")
    status: ProjectStatus = Field(..., description="프로젝트 상태")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")
    test_required: bool = Field(..., description="AI 테스트 필수 여부")
    views: int = Field(..., description="조회수")
    user_id: str = Field(..., description="팀장 ID (UUID)")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    id: int = Field(..., description="프로젝트 ID")
    title: str = Field(..., description="프로젝트 제목")
    description: str = Field(..., description="프로젝트 설명")
    type: ProjectType = Field(..., description="프로젝트 타입")
    method: ProjectMethod = Field(..., description="진행 방식")
    status: ProjectStatus = Field(..., description="프로젝트 상태")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")
    test_required: bool = Field(..., description="AI 테스트 필수 여부")
    views: int = Field(..., description="조회수")
    user_id: str = Field(..., description="팀장 ID (UUID)")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")
    recruitment_positions: List[RecruitmentPositionResponse] = Field(..., description="모집 포지션 목록")

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary] = Field(..., description="프로젝트 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse] = Field(..., description="지원서 목록")
    total: int = Field(..., description="전체 개수")
    pending_count: int = Field(..., description="대기 중인 지원서 수")
    accepted_count: int = Field(..., description="승인된 지원서 수")
    rejected_count: int = Field(..., description="거절된 지원서 수")


# Query Parameters
class ProjectFilters(BaseModel):
    type: Optional[ProjectType] = Field(None, description="프로젝트 타입 필터")
    status: Optional[ProjectStatus] = Field(None, description="프로젝트 상태 필터")
    tech_stack: Optional[str] = Field(None, description="기술 스택 필터")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(10, ge=1, le=100, description="페이지 크기")


class ApplicationFilters(BaseModel):
    status: Optional[ApplicationStatus] = Field(None, description="지원서 상태 필터")
    position_type: Optional[PositionType] = Field(None, description="포지션 타입 필터")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(10, ge=1, le=100, description="페이지 크기")