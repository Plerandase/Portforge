from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.enums import UserRole, StackCategory, TechStack

class UserBase(BaseModel):
    email: EmailStr
    nickname: str
    profile_image_url: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserResponse(UserBase):
    user_id: str
    role: UserRole
    liked_project_ids: Optional[List[int]] = None
    test_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserStackBase(BaseModel):
    position_type: StackCategory
    stack_name: TechStack

class UserStackCreate(UserStackBase):
    pass

class UserStackResponse(UserStackBase):
    stack_id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True