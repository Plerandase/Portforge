from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings # 설정 객체 로드
import aioboto3

# MySQL aiomysql 비동기 연결 설정
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # SQL 로그 비활성화 (성능 향상)
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,   # 1시간마다 연결 재생성
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

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

aws_manager = AWSManager()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()