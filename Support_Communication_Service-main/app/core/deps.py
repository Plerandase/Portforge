from fastapi import Header, HTTPException, status
from typing import Optional, Dict, Any
import json
import base64
import logging

logger = logging.getLogger(__name__)


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Authorization 헤더에서 사용자 정보를 추출합니다.
    - Bearer 토큰이 있으면 JWT 페이로드에서 email 추출
    - email로 Auth Service API 호출하여 실제 user_id 반환
    - 없으면 더미 사용자 반환
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            # JWT 페이로드 추출 (검증 없이)
            parts = token.split(".")
            if len(parts) >= 2:
                # Base64 디코딩
                payload_b64 = parts[1]
                # 패딩 추가
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload_json = base64.urlsafe_b64decode(payload_b64)
                payload = json.loads(payload_json)
                
                email = payload.get("email")
                jwt_sub = payload.get("sub")
                
                logger.info(f"✅ JWT 파싱 성공: email={email}, sub={jwt_sub}")
                
                # email로 Auth Service API 호출
                if email:
                    try:
                        from app.utils.msa_client import msa_client
                        user_data = await msa_client.get_user_by_email(email)
                        
                        if user_data:
                            # Auth Service가 직접 데이터를 반환 (ResponseEnvelope 없음)
                            logger.info(f"✅ Auth Service 조회 성공: user_id={user_data.get('user_id')}")
                            return {
                                "id": user_data.get("user_id"),
                                "email": user_data.get("email"),
                                "nickname": user_data.get("nickname"),
                            }
                        else:
                            logger.warning(f"⚠️ Auth Service에 사용자 없음: email={email}")
                    except Exception as e:
                        logger.error(f"⚠️ Auth Service 조회 실패: {e}")
                
                # Auth Service 조회 실패 시 JWT의 sub 사용 (fallback)
                if jwt_sub:
                    logger.warning(f"⚠️ Auth Service 조회 실패 - JWT sub 사용: {jwt_sub}")
                    return {
                        "id": jwt_sub,
                        "email": email or "",
                        "nickname": payload.get("nickname", "") or payload.get("cognito:username", ""),
                    }
        except Exception as e:
            logger.error(f"❌ 토큰 파싱 실패: {e}")
    
    # 토큰이 없거나 파싱 실패 시 더미 사용자 반환
    logger.warning("⚠️ 토큰 없음 또는 파싱 실패 - 더미 사용자 반환")
    return {
        "id": "1",
        "email": "demo@example.com",
        "name": "Demo User",
        "nickname": "demo",
    }


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """Allows unauthenticated access but still returns a dummy user if a header is present."""
    if not authorization:
        return None
    return await get_current_user(authorization)


