from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TestResultResponse(BaseModel):
    result_id: int
    user_id: str
    project_id: Optional[int] = None
    application_id: Optional[int] = None
    test_type: str
    score: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    portfolio_id: int
    user_id: str
    project_id: int
    title: str
    summary: Optional[str] = None
    role_description: Optional[str] = None
    problem_solving: Optional[str] = None
    tech_stack_usage: Optional[str] = None
    growth_point: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True