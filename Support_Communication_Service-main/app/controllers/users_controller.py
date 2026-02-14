from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    name: str | None = None
    bio: str | None = None
    stacks: list[str] | None = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


@router.get("/me", response_model=ResponseEnvelope)
async def get_me(current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="USER_000", message="Current user", data=current_user)


@router.get("/{user_id}/profile", response_model=ResponseEnvelope)
async def get_profile(user_id: int):
    profile = {
        "id": user_id,
        "name": "User Name",
        "nickname": "nickname",
        "bio": "This is a sample profile.",
        "stacks": ["python", "fastapi"],
    }
    return ResponseEnvelope(success=True, code="USER_001", message="Profile", data=profile)


@router.patch("/{user_id}/profile", response_model=ResponseEnvelope)
async def update_profile(user_id: int, payload: ProfileUpdate, current_user=Depends(get_current_user)):
    updated = {"id": user_id, **payload.model_dump(exclude_none=True)}
    return ResponseEnvelope(success=True, code="USER_002", message="Profile updated", data=updated)


@router.post("/{user_id}/profile/image", response_model=ResponseEnvelope)
async def upload_profile_image(user_id: int, file: UploadFile = File(...), current_user=Depends(get_current_user)):
    url = f"https://cdn.example.com/profiles/{user_id}/{file.filename}"
    return ResponseEnvelope(success=True, code="USER_003", message="Profile image set", data={"url": url})


@router.put("/{user_id}/password", response_model=ResponseEnvelope)
async def change_password(user_id: int, payload: PasswordUpdate, current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="USER_004", message="Password changed", data=None)


@router.get("/{user_id}/projects/{project_id}/application", response_model=ResponseEnvelope)
async def get_application(user_id: int, project_id: int, current_user=Depends(get_current_user)):
    application = {
        "user_id": user_id,
        "project_id": project_id,
        "status": "pending",
        "applied_at": "2024-01-01T00:00:00Z",
    }
    return ResponseEnvelope(success=True, code="USER_005", message="Application status", data=application)


@router.get("/{user_id}/test_result", response_model=ResponseEnvelope)
async def get_test_result(user_id: int, current_user=Depends(get_current_user)):
    result = {
        "user_id": user_id,
        "score": 85,
        "strengths": ["problem solving", "collaboration"],
        "weaknesses": ["time management"],
    }
    return ResponseEnvelope(success=True, code="USER_006", message="Test result", data=result)
