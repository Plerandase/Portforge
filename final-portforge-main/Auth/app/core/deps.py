# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import cognito_verifier

# Swagger UI에서 'Authorize' 버튼을 통해 토큰을 입력받을 수 있게 해줍니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    모든 API의 입구에서 실행될 공통 로직입니다.
    유효한 유저라면 Cognito의 페이로드(sub, email 등)를 반환합니다.
    """
    # 1. 보안 엔진을 통해 토큰 검증
    payload = await cognito_verifier.verify_token(token)
    
    # 2. 유저 고유 식별값(sub) 확인
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identifier (sub) missing in token",
        )
    
    # 3. 인증된 유저의 정보를 반환 (나중에 클래스 객체로 변환 가능)
    return payload