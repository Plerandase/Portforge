"""
AI 서비스 테이블 생성 스크립트 (Phase 1, 2 Updated)
동기 방식으로 테이블을 생성합니다.
MeetingSession, GeneratedReport 테이블은 Team-BE로 이관됨
"""
import sys
import os

# pymysql 설치 확인
try:
    import pymysql
except ImportError:
    print("📦 pymysql 설치 중...")
    os.system(f"{sys.executable} -m pip install pymysql cryptography -q")
    import pymysql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

DATABASE_URL = "mysql+pymysql://root:rootpassword@localhost:3306/portforge_ai"

def create_tables():
    """테이블 생성"""
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        Base = declarative_base()
        
        from sqlalchemy import Column, String, DateTime, BigInteger, Text, Boolean, JSON
        
        class Test(Base):
            __tablename__ = "tests"
            
            test_id = Column(BigInteger, primary_key=True, autoincrement=True)
            stack_name = Column(String(50), nullable=False)
            question_json = Column(JSON, nullable=False)
            difficulty = Column(String(20), default="초급")
            source_prompt = Column(Text, nullable=True)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        class TestResult(Base):
            __tablename__ = "test_results"
            
            result_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(String(36), nullable=False)
            project_id = Column(BigInteger, nullable=True)
            application_id = Column(BigInteger, unique=True, nullable=True)
            test_type = Column(String(20), default="APPLICATION")
            score = Column(BigInteger, nullable=True)
            feedback = Column(Text, nullable=True)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        class Portfolio(Base):
            __tablename__ = "portfolios"
            
            portfolio_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(String(36), nullable=False)
            project_id = Column(BigInteger, nullable=False)
            title = Column(String(200), default='프로젝트 회고록')
            summary = Column(Text, nullable=True)
            role_description = Column(Text, nullable=True)
            problem_solving = Column(Text, nullable=True)
            tech_stack_usage = Column(Text, nullable=True)
            growth_point = Column(Text, nullable=True)
            external_links = Column(Text, nullable=True)  # 증빙 자료 링크
            thumbnail_url = Column(String(1024), nullable=True)
            is_public = Column(Boolean, default=True)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        print("Creating AI tables (Phase 1, 2 Updated)...")
        print("Note: MeetingSession, GeneratedReport are now in Team-BE")
        Base.metadata.drop_all(bind=engine)  # 기존 테이블 삭제
        Base.metadata.create_all(bind=engine)
        print("AI tables created successfully!")
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
