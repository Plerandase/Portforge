from typing import Optional, List
from pydantic import BaseModel
from app.models.enums import UserRole, StackCategory, TechStack
from app.schemas.user import UserSimple

class UserUpdate(BaseModel):
    name: Optional[str] = None
    myStacks: Optional[List[str]] = None
    profile_image_url: Optional[str] = None  # 프로필 이미지 URL (Base64 또는 URL)

    class Config:
        from_attributes = True
