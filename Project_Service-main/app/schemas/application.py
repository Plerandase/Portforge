from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# Request Schemas
class ApplicationCreate(BaseModel):
    position: str = Field(..., min_length=1, max_length=100)
    motivation: Optional[str] = Field(None, max_length=2000)
    experience: Optional[str] = Field(None, max_length=2000)
    portfolio: Optional[str] = Field(None, max_length=500)
    available_hours: Optional[str] = Field(None, max_length=100)
    contact: Optional[str] = Field(None, max_length=200)
    skills: Optional[str] = Field(None, max_length=1000)
    questions: Optional[str] = Field(None, max_length=1000)
    ai_test_score: Optional[int] = Field(None, ge=0, le=100)
    ai_test_level: Optional[str] = Field(None, max_length=50)
    ai_test_feedback: Optional[str] = Field(None, max_length=1000)


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


# Response Schemas
class ApplicationResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    position: str
    message: Optional[str] = None
    motivation: Optional[str]
    experience: Optional[str]
    portfolio: Optional[str]
    available_hours: Optional[str]
    contact: Optional[str]
    skills: Optional[str]
    questions: Optional[str]
    ai_test_score: Optional[int]
    ai_test_level: Optional[str]
    ai_test_feedback: Optional[str]
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationSummary(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None  # 사용자 이름 (별도 조회 필요)
    position: str
    message: Optional[str] = None
    ai_test_score: Optional[int]
    ai_test_level: Optional[str]
    status: ApplicationStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationSummary]
    total: int
    pending_count: int
    accepted_count: int
    rejected_count: int