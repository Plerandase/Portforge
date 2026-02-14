from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Base 클래스
Base = declarative_base()

# 비동기 엔진 생성 (config에서 URL 가져오기)
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,
    pool_recycle=300
)

# 비동기 세션 팩토리
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 데이터베이스 세션 의존성
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
