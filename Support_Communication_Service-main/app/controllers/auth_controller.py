from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    provider: str | None = None


class JoinRequest(BaseModel):
    email: str
    password: str
    name: str
    nickname: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=ResponseEnvelope)
async def login(payload: LoginRequest):
    token = {
        "access_token": "demo-token",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    user = {
        "id": 1,
        "email": payload.email or "demo@example.com",
        "name": "Demo User",
        "nickname": "demo",
    }
    return ResponseEnvelope(success=True, code="AUTH_000", message="Logged in", data={"token": token, "user": user})


@router.post("/logout", response_model=ResponseEnvelope)
async def logout(current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="AUTH_000", message="Logged out", data=None)


@router.post("/join", response_model=ResponseEnvelope, status_code=201)
async def join(payload: JoinRequest):
    created = {
        "id": 2,
        "email": payload.email,
        "name": payload.name,
        "nickname": payload.nickname,
    }
    return ResponseEnvelope(success=True, code="AUTH_001", message="User registered", data=created)


@router.get("/validate_nickname", response_model=ResponseEnvelope)
async def validate_nickname(nickname: str = Query(...)):
    is_available = nickname.lower() != "taken"
    return ResponseEnvelope(
        success=is_available,
        code="AUTH_002",
        message="Nickname available" if is_available else "Nickname already in use",
        data={"nickname": nickname, "available": is_available},
    )
