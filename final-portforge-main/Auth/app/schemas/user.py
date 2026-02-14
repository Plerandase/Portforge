from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class StackCategory(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DB = "DB"
    INFRA = "INFRA"
    DESIGN = "DESIGN"
    ETC = "ETC"

class TechStack(str, Enum):
    React = "React"
    Vue = "Vue"
    Nextjs = "Nextjs"
    TypeScript = "TypeScript"
    JavaScript = "JavaScript"
    Java = "Java"
    Spring = "Spring"
    Nodejs = "Nodejs"
    Python = "Python"
    Django = "Django"
    Flask = "Flask"
    MySQL = "MySQL"
    PostgreSQL = "PostgreSQL"
    MongoDB = "MongoDB"
    Redis = "Redis"
    AWS = "AWS"
    Docker = "Docker"
    Kubernetes = "Kubernetes"

class UserResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    role: UserRole
    profile_image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserStackResponse(BaseModel):
    stack_id: int
    position_type: StackCategory
    stack_name: TechStack
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserDetailResponse(UserResponse):
    liked_project_ids: List[int] = []
    test_count: int
    updated_at: Optional[datetime] = None
    stacks: List[UserStackResponse] = []

    class Config:
        from_attributes = True

class UserSimple(BaseModel):
    user_id: str
    email: str
    nickname: str
    profile_image_url: Optional[str] = None
    role: UserRole
    myStacks: List[str] = []
    test_count: int = 5
    liked_project_ids: List[int] = []

    class Config:
        from_attributes = True

class UserStackCreate(BaseModel):
    position_type: StackCategory
    stack_name: TechStack

class UserCreate(BaseModel):
    email: str
    password: str
    nickname: str
    role: UserRole = UserRole.USER
    stacks: List[UserStackCreate] = []

    class Config:
        from_attributes = True

class NicknameCheckResponse(BaseModel):
    is_available: bool

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(BaseModel):
    access_token: str
    id_token: Optional[str] = None
    token_type: str
    user: UserSimple

class EmailVerification(BaseModel):
    email: str
    code: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ConfirmForgotPassword(BaseModel):
    email: str
    code: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    password: str
    reason: Optional[str] = None

class DeleteAccountResponse(BaseModel):
    message: str
    deleted_at: str