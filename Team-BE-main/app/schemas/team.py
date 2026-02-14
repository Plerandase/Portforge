from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TeamRole(str, Enum):
    LEADER = "LEADER"
    MEMBER = "MEMBER"

class StackCategory(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DB = "DB"
    INFRA = "INFRA"
    DESIGN = "DESIGN"
    ETC = "ETC"

class TeamResponse(BaseModel):
    team_id: int
    project_id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class TeamMemberResponse(BaseModel):
    team_id: int
    user_id: str
    role: TeamRole
    position_type: StackCategory
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TeamDetailResponse(TeamResponse):
    updated_at: Optional[datetime] = None
    members: List[TeamMemberResponse] = []

    class Config:
        from_attributes = True