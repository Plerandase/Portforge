# app/core/config.py - Pydantic Settings 기반 설정 관리
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # [App Settings]
    PROJECT_NAME: str = "Portforge-Auth"
    ENV: str = "local"
    DEBUG: bool = True

    # [Database - MySQL]
    DATABASE_URL: str = ""

    # [AWS Infrastructure]
    AWS_REGION: str = "ap-northeast-2"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # [AWS S3]
    S3_BUCKET_TEAM: str = "portforge-team"

    # [AWS Cognito - Auth]
    # .env 파일에서 COGNITO_USERPOOL_ID 또는 COGNITO_USER_POOL_ID 둘 다 지원
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_USERPOOL_ID: str = ""  # 기존 .env 호환용
    COGNITO_APP_CLIENT_ID: str = ""
    COGNITO_DOMAIN: str = ""
    REDIRECT_URI: str = "http://localhost:3000/#/auth/callback"
    
    @property
    def EFFECTIVE_USER_POOL_ID(self) -> str:
        """COGNITO_USER_POOL_ID 또는 COGNITO_USERPOOL_ID 중 값이 있는 것을 반환"""
        return self.COGNITO_USER_POOL_ID or self.COGNITO_USERPOOL_ID
    
    # [Security - JWT Settings]
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWKS_TIMEOUT: int = 10
    
    # [MSA Service URLs]
    AUTH_SERVICE_URL: str = "http://auth-service"
    PROJECT_SERVICE_URL: str = "http://project-service"
    TEAM_SERVICE_URL: str = "http://team-service"
    AI_SERVICE_URL: str = "http://ai-service"
    SUPPORT_SERVICE_URL: str = "http://support-service"
    
    # [CORS]
    CORS_ORIGINS: str = "*"

    @property
    def COGNITO_JWKS_URL(self) -> str:
        """AWS Region과 UserPool ID를 조합하여 JWKS 주소를 생성합니다."""
        return f"https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.EFFECTIVE_USER_POOL_ID}/.well-known/jwks.json"

    # Pydantic Settings 설정
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "Auth/.env"], 
        env_file_encoding="utf-8",
        extra="ignore" 
    )

# 인스턴스화
settings = Settings()

# 디버깅용 출력
print(f"🔧 [Config] COGNITO_REGION: {settings.AWS_REGION}")
print(f"🔧 [Config] COGNITO_USER_POOL_ID: {settings.EFFECTIVE_USER_POOL_ID}")
print(f"🔧 [Config] COGNITO_APP_CLIENT_ID: {settings.COGNITO_APP_CLIENT_ID}")
print(f"🔧 [Config] JWKS_URL: {settings.COGNITO_JWKS_URL}")