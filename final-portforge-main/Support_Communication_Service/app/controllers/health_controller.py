from fastapi import APIRouter
from sqlalchemy import text

from app.schemas.base import ResponseEnvelope
from app.core.database import engine

router = APIRouter()


@router.get("/liveness", response_model=ResponseEnvelope)
async def liveness_check():
    """서버가 살아있는지 확인 (Liveness)"""
    return ResponseEnvelope(success=True, code="COMMON_000", message="Alive", data=None)


@router.get("/readiness", response_model=ResponseEnvelope)
async def readiness_check():
    """DB 연결 여부 확인 (Readiness)"""
    checks = {}
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "connected"
        db_ok = True
    except Exception as e:
        checks["database"] = f"error: {e.__class__.__name__}"
        db_ok = False

    success = db_ok
    code = "COMMON_000" if success else "COMMON_999"
    msg = "Ready" if success else "Not ready"
    return ResponseEnvelope(success=success, code=code, message=msg, data=checks)
