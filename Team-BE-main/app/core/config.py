from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 데이터베이스 설정 (MySQL 사용)
    DATABASE_URL: str = "mysql+aiomysql://root:rootpassword@localhost:3306/portforge_team"
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS S3 설정
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-2"
    S3_BUCKET_TEAM: str = "portforge-team"
    S3_BUCKET_LOG: str = "portforge-log"
    S3_BUCKET_FRONT: str = "portforge-front"
    
    # DynamoDB 설정
    DDB_ENDPOINT_URL: str = ""
    DYNAMODB_TABLE_CHATS: str = "team_chats"
    DYNAMODB_TABLE_ROOMS: str = "chat_rooms"
    
    # [MSA Service URLs]
    AUTH_SERVICE_URL: str = "http://auth-service"
    PROJECT_SERVICE_URL: str = "http://project-service"
    TEAM_SERVICE_URL: str = "http://team-service"
    AI_SERVICE_URL: str = "http://ai-service"
    SUPPORT_SERVICE_URL: str = "http://support-service"
    
    # [Frontend URL]
    FRONTEND_URL: str = "http://localhost:3000"
    
    # [CORS]
    CORS_ORIGINS: str = "*"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()