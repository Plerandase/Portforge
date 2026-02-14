# app/api/deps.py

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import os
import requests
import traceback

from app.db.session import get_db
from app.models.user import User

# 1. 환경변수 설정 및 검증
# app.core.config의 settings 객체 사용 (환경변수 매핑 자동 처리됨)
from app.core.config import settings

COGNITO_REGION = settings.AWS_REGION
COGNITO_USER_POOL_ID = settings.EFFECTIVE_USER_POOL_ID
COGNITO_APP_CLIENT_ID = settings.COGNITO_APP_CLIENT_ID

# 환경변수 검증
print(f"🔧 [deps] COGNITO_REGION: {COGNITO_REGION}")
print(f"🔧 [deps] COGNITO_USER_POOL_ID: {COGNITO_USER_POOL_ID}")
print(f"🔧 [deps] COGNITO_APP_CLIENT_ID: {COGNITO_APP_CLIENT_ID}")

if not COGNITO_USER_POOL_ID:
    print("❌ [Config] COGNITO_USER_POOL_ID 환경변수가 설정되지 않았습니다!")
    
if not COGNITO_APP_CLIENT_ID:
    print("❌ [Config] COGNITO_APP_CLIENT_ID 환경변수가 설정되지 않았습니다!")

# Cognito 공개 키(JWKS) 주소 생성
# settings 객체에 정의된 프로퍼티 사용
JWKS_URL = settings.COGNITO_JWKS_URL
print(f"🔧 [Config] JWKS_URL: {JWKS_URL}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 환경변수 필수 체크
    if not COGNITO_USER_POOL_ID or not COGNITO_APP_CLIENT_ID:
        print("❌ [Auth] Cognito 환경변수가 설정되지 않았습니다!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 설정 오류: Cognito 환경변수 누락"
        )

    try:
        print(f"🔍 [Auth] 토큰 검증 시작. JWKS URL: {JWKS_URL}")
        
        # 2. Cognito 공개 키(JWKS) 다운로드
        try:
            jwks_response = requests.get(JWKS_URL, timeout=10)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
            print(f"✅ [Auth] JWKS 다운로드 성공")
        except requests.RequestException as e:
            print(f"❌ [Auth] JWKS 다운로드 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cognito JWKS 다운로드 실패: {str(e)}"
            )
        
        # 3. 토큰 헤더에서 Key ID(kid) 추출
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            print(f"🔍 [Auth] 토큰 헤더: {unverified_header}")
        except Exception as e:
            print(f"❌ [Auth] 토큰 헤더 파싱 실패: {str(e)}")
            raise credentials_exception
            
        if not kid:
            print("❌ [Auth] 토큰 헤더에 kid가 없습니다.")
            raise credentials_exception

        # 4. JWKS에서 현재 토큰과 맞는 키 찾기
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            print(f"❌ [Auth] JWKS에서 일치하는 키를 찾지 못했습니다. kid: {kid}")
            print(f"🔍 [Auth] 사용 가능한 키들: {[k.get('kid') for k in jwks.get('keys', [])]}")
            raise credentials_exception

        print(f"✅ [Auth] RSA 키 찾기 성공. kid: {kid}")

# 5. 토큰 검증 및 해독 (RS256 방식)
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=COGNITO_APP_CLIENT_ID,
                options={"verify_at_hash": False}
            )
            print(f"✅ [Auth] JWT 토큰 검증 성공")
        except Exception as e:
            print(f"❌ [Auth] JWT 검증 실패: {str(e)}")
            raise credentials_exception

        # 🔍 [추가된 디버깅] 토큰 내부 데이터 출력
        print(f"🔍 [Auth] 토큰 페이로드: {payload}")

        # 6. 식별자(이메일) 추출 로직 강화
        # 1순위: 'email' 필드 확인 (ID Token 사용 시)
        # 2순위: 'cognito:username' 확인 (일부 설정에서 이메일이 여기 들어감)
        email = payload.get("email") or payload.get("cognito:username")
        
        # 만약 이메일 형태(@ 포함)가 아니거나 없으면 sub(UUID)를 가져옵니다.
        if not email or "@" not in str(email):
            print(f"⚠️ [Auth] 이메일 형식을 찾지 못함. sub 값 사용 시도: {payload.get('sub')}")
            email = payload.get("sub")

        if not email:
            print(f"❌ [Auth] 식별자 추출 실패. 페이로드: {payload}")
            raise credentials_exception

        print(f"✅ [Auth] 최종 추출된 식별자: {email}")

    except Exception as e:
        # 에러 발생 시 로그 출력
        print(f"❌ [Auth] 인증 과정 중 오류 발생: {str(e)}")
        raise credentials_exception

    # 7. DB에서 유저 조회 (Email 컬럼과 비교)
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        print(f"❌ [Auth] DB에 사용자 정보가 없습니다: {email}")
        raise credentials_exception
    
    print(f"✅ [Auth] 사용자 로그인 유지 성공: {user.email}")
    return user