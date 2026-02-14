# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# settings에서 DATABASE_URL을 가져옵니다.
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# aiomysql 드라이버를 pymysql로 변환 (동기 API용)
# 비동기 드라이버는 동기 함수에서 사용할 수 없음
if SQLALCHEMY_DATABASE_URL and "aiomysql" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("aiomysql", "pymysql")

# DB 연결 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델들이 상속받을 기본 클래스
Base = declarative_base()

# 의존성 주입용 함수 (API에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
