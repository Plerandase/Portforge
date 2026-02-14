"""
Project 서비스 테이블 생성 스크립트 (Phase 1, 2 Updated)
동기 방식으로 테이블을 생성합니다.
employment_type 컬럼이 삭제됨
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

DATABASE_URL = "mysql+pymysql://root:rootpassword@localhost:3306/portforge_project"

def create_tables():
    """테이블 생성"""
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        Base = declarative_base()
        
        from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, BigInteger, Text, Boolean, Date, ForeignKey
        from sqlalchemy.dialects.mysql import CHAR
        import enum
        
        class ProjectType(str, enum.Enum):
            PROJECT = "PROJECT"
            STUDY = "STUDY"
        
        class ProjectMethod(str, enum.Enum):
            ONLINE = "ONLINE"
            OFFLINE = "OFFLINE"
            MIXED = "MIXED"
        
        class ProjectStatus(str, enum.Enum):
            RECRUITING = "RECRUITING"
            PROCEEDING = "PROCEEDING"
            COMPLETED = "COMPLETED"
            CLOSED = "CLOSED"
        
        class PositionType(str, enum.Enum):
            FRONTEND = "FRONTEND"
            BACKEND = "BACKEND"
            DB = "DB"
            INFRA = "INFRA"
            DESIGN = "DESIGN"
            ETC = "ETC"
            STUDY_MEMBER = "STUDY_MEMBER"
        
        class ApplicationStatus(str, enum.Enum):
            PENDING = "PENDING"
            ACCEPTED = "ACCEPTED"
            REJECTED = "REJECTED"
        
        class Project(Base):
            __tablename__ = "projects"
            
            project_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(CHAR(36), nullable=False, comment="팀장 ID")
            type = Column(SQLEnum(ProjectType), nullable=False)
            title = Column(String(100), nullable=False)
            description = Column(Text, nullable=False)
            method = Column(SQLEnum(ProjectMethod), nullable=False, default=ProjectMethod.ONLINE)
            status = Column(SQLEnum(ProjectStatus), nullable=False, default=ProjectStatus.RECRUITING)
            start_date = Column(Date, nullable=False)
            end_date = Column(Date, nullable=False)
            test_required = Column(Boolean, nullable=False, default=False)
            views = Column(Integer, nullable=False, default=0)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        class ProjectRecruitmentPosition(Base):
            __tablename__ = "project_recruitment_positions"
            
            project_id = Column(BigInteger, ForeignKey("projects.project_id", ondelete="CASCADE"), primary_key=True, nullable=False)
            position_type = Column(SQLEnum(PositionType), primary_key=True, nullable=False)
            required_stacks = Column(Text, nullable=True)
            # employment_type 삭제됨
            target_count = Column(Integer, nullable=True)
            current_count = Column(Integer, nullable=False, default=0)
            recruitment_deadline = Column(Date, nullable=True)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        class Application(Base):
            __tablename__ = "applications"
            
            application_id = Column(BigInteger, primary_key=True, autoincrement=True)
            project_id = Column(BigInteger, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
            user_id = Column(CHAR(36), nullable=False)
            position_type = Column(SQLEnum(PositionType), nullable=False)
            message = Column(Text, nullable=False)
            status = Column(SQLEnum(ApplicationStatus), nullable=False, default=ApplicationStatus.PENDING)
            created_at = Column(DateTime, nullable=False, default=func.now())
            updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
        
        print("Creating Project tables (Phase 1, 2 Updated)...")
        print("Note: employment_type column has been removed")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Project tables created successfully!")
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
