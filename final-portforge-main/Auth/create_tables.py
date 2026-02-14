"""
Auth 서비스 테이블 생성 스크립트 (Phase 1, 2 Updated)
동기 방식으로 테이블을 생성합니다.
"""
import sys
import os

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

DATABASE_URL = "mysql+pymysql://root:rootpassword@localhost:3306/portforge_auth"

def create_tables():
    """테이블 생성"""
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        Base = declarative_base()
        
        from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, BigInteger, Text, JSON, ForeignKey
        from sqlalchemy.dialects.mysql import CHAR
        import enum
        
        class UserRole(str, enum.Enum):
            USER = "USER"
            ADMIN = "ADMIN"
        
        class StackCategory(str, enum.Enum):
            FRONTEND = "FRONTEND"
            BACKEND = "BACKEND"
            DB = "DB"
            INFRA = "INFRA"
            DESIGN = "DESIGN"
            ETC = "ETC"
        
        class User(Base):
            __tablename__ = "users"
            
            user_id = Column(CHAR(36), primary_key=True)
            email = Column(String(100), unique=True, nullable=False)
            nickname = Column(String(20), nullable=False)
            role = Column(SQLEnum(UserRole), default=UserRole.USER)
            profile_image_url = Column(Text, nullable=True)
            liked_project_ids = Column(JSON, nullable=True)
            test_count = Column(Integer, default=5)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        class UserStack(Base):
            __tablename__ = "user_stacks"
            
            stack_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(CHAR(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
            position_type = Column(SQLEnum(StackCategory), nullable=False)
            stack_name = Column(String(50), nullable=False)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        print("Creating Auth tables (Phase 1, 2 Updated)...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Auth tables created successfully!")
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
