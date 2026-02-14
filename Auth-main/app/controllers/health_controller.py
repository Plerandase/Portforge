from fastapi import APIRouter
from app.schemas.base import ResponseEnvelope
router = APIRouter()

@router.get("/liveness", response_model=ResponseEnvelope)
async def liveness_check():
    """서버가 살아있는지 확인 (Liveness)"""
    return ResponseEnvelope(success=True, code="COMMON_000", message="Alive", data=None)

@router.get("/readiness", response_model=ResponseEnvelope)
async def readiness_check():
    """의존성(DB, Redis 등)이 준비되었는지 확인 (Readiness)"""
    # 💡 아키텍트의 팁: 3단계에서 DB가 추가되면 여기에 'DB 연결 체크' 로직을 넣습니다.
    # 현재는 준비된 상태로 가정합니다.
    checks = {
        "database": "connected", # 나중에 실제 체크로 대체
        "redis": "connected"     # 나중에 실제 체크로 대체
    }
    return ResponseEnvelope(success=True, code="COMMON_000", message="Ready", data=checks)
