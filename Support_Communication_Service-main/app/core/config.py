from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # [App Settings]
    PROJECT_NAME: str = "Jerry-Architect-Template"
    ENV: str = "local"
    DEBUG: bool = True

    # [Database - MySQL]
    DATABASE_URL: str = ""

    # [AWS Infrastructure - LocalStack/MinIO]
    DDB_ENDPOINT_URL: str = ""
    S3_ENDPOINT_URL: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-2"
    
    # [DynamoDB Tables]
    DYNAMODB_TABLE_CHATS: str = "team_chats_ddb"
    DYNAMODB_TABLE_ROOMS: str = "chat_rooms_ddb"

    # [AWS Cognito - Auth]
    COGNITO_REGION: str = ""
    COGNITO_USERPOOL_ID: str = ""
    COGNITO_APP_CLIENT_ID: str = ""
    
    # [MSA Service URLs]
    AUTH_SERVICE_URL: str = "http://auth-service"
    PROJECT_SERVICE_URL: str = "http://project-service"
    TEAM_SERVICE_URL: str = "http://team-service"
    AI_SERVICE_URL: str = "http://ai-service"
    SUPPORT_SERVICE_URL: str = "http://support-service"
    
    # [CORS]
    CORS_ORIGINS: str = "*"
    
    # [Security - JWT Settings]
    # Cognito는 RS256을 사용하므로 알고리즘을 고정합니다.
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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