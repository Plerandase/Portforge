from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings # 설정 객체 로드
import aioboto3

# 1. MySQL 설정 (환경 변수 적용)
# DB URL이 비어있을 경우에 대한 방어 로직 (로컬 개발용 SQLite Fallback 등 고려 가능하나 일단 유지)
engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

# Dependency Injection용 get_db 함수 추가
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 2. AWS 서비스 매니저 (환경 변수 적용)
class AWSManager:
    def __init__(self):
        self.session = aioboto3.Session()

    def get_ddb_client(self):
        return self.session.client(
            'dynamodb', 
            endpoint_url=settings.DDB_ENDPOINT_URL, 
            region_name=settings.AWS_REGION
        )

    def get_s3_client(self):
        return self.session.client(
            's3', 
            endpoint_url=settings.S3_ENDPOINT_URL, 
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="us-east-1"
        )
    
    def get_s3_adapter(self):
        """S3Adapter 싱글톤 반환 (meeting_service 호환용)"""
        from app.adapters.s3_adapter import s3_adapter
        return s3_adapter

aws_manager = AWSManager()