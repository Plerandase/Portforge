import httpx
from jose import jwt, jwk
from jose.utils import base64url_decode
from fastapi import HTTPException, status
from app.core.config import settings

class CognitoVerifier:
    def __init__(self):
        self.jwks = None

    async def _get_jwks(self):
        """AWS에서 공개키 목록을 비동기로 가져와 캐싱합니다."""
        if not self.jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.COGNITO_JWKS_URL)
                self.jwks = response.json()["keys"]
        return self.jwks

    async def verify_token(self, token: str):
        """Cognito 토큰의 서명과 유효성을 검증합니다."""
        try:
            # 1. 서명 키(kid) 확인
            headers = jwt.get_unverified_header(token)
            kid = headers.get("kid")

            # 2. 일치하는 공개키 찾기
            keys = await self._get_jwks()
            key_data = next((k for k in keys if k["kid"] == kid), None)
            if not key_data:
                raise HTTPException(status_code=401, detail="Public key not found")

            # 3. RS256 방식으로 검증 및 페이로드 추출
            payload = jwt.decode(
                token,
                key_data,
                algorithms=["RS256"],
                audience=settings.COGNITO_APP_CLIENT_ID,
                # 발급자(iss) 확인 로직 포함
                issuer=f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USERPOOL_ID}"
            )
            return payload

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Cognito Token: {str(e)}"
            )

cognito_verifier = CognitoVerifier()