from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# .env 파일을 시스템 환경변수보다 우선하도록 강제 로드
load_dotenv(override=True)

class Settings(BaseSettings):
    # [App Settings]
    PROJECT_NAME: str = "Portforge-AI-Service"
    ENV: str = "local"
    DEBUG: bool = True

    # [Database - MySQL]
    DATABASE_URL: str = ""

    # [AWS S3 설정]
    S3_BUCKET_TEAM: str = "portforge-team"
    S3_BUCKET_LOG: str = "portforge-log"
    S3_BUCKET_FRONT: str = "portforge-front"
    S3_PREFIX: str = "ai/"

    # [DynamoDB 설정]
    DDB_ENDPOINT_URL: str = ""
    DDB_TABLE_NAME: str = "team_chats"

    # [AWS 설정]
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-2"
    
    # [AWS Bedrock 설정] - Claude 3.5 Sonnet v1 (On-demand)
    BEDROCK_REGION: str = "ap-northeast-2"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # [AWS Cognito - Auth]
    COGNITO_REGION: str = ""
    COGNITO_USERPOOL_ID: str = ""
    COGNITO_APP_CLIENT_ID: str = ""
    
    # [Security - JWT Settings]
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
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
        """AWS에서 제공하는 공개키 목록 주소를 동적으로 생성합니다."""
        return f"https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.COGNITO_USERPOOL_ID}/.well-known/jwks.json"

    # Pydantic Settings 설정
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" 
    )

# 인스턴스화
settings = Settings() # type: ignore