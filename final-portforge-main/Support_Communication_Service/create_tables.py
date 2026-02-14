"""
Support 서비스 테이블 생성 스크립트 (Phase 1, 2 Updated)
동기 방식으로 테이블을 생성합니다.
event_description -> description, event_date -> start_date 변경됨
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

DATABASE_URL = "mysql+pymysql://root:rootpassword@localhost:3306/portforge_support"

def create_tables():
    """테이블 생성"""
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        Base = declarative_base()
        
        from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, BigInteger, Text, Boolean
        import enum
        
        class ProjectReportType(str, enum.Enum):
            REPORT = "REPORT"
            INQUIRY = "INQUIRY"
            BUG = "BUG"
        
        class ProjectReportStatus(str, enum.Enum):
            PENDING = "PENDING"
            IN_PROGRESS = "IN_PROGRESS"
            RESOLVED = "RESOLVED"
            DISMISSED = "DISMISSED"
        
        class EventCategory(str, enum.Enum):
            CONTEST = "CONTEST"
            HACKATHON = "HACKATHON"
        
        class ProjectReport(Base):
            __tablename__ = "project_reports"
            
            report_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(String(36), nullable=False, index=True)
            project_id = Column(BigInteger, nullable=False, index=True)
            type = Column(SQLEnum(ProjectReportType), nullable=False)
            content = Column(Text, nullable=False)
            status = Column(SQLEnum(ProjectReportStatus), nullable=False, server_default=ProjectReportStatus.PENDING.value)
            resolution_note = Column(Text)
            created_at = Column(DateTime, nullable=False, server_default=func.now())
            updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
        
        class Notification(Base):
            __tablename__ = "notifications"
            
            notification_id = Column(BigInteger, primary_key=True, autoincrement=True)
            user_id = Column(String(36), nullable=False, index=True)
            message = Column(Text)
            link = Column(Text)
            is_read = Column(Boolean, nullable=False, server_default="0")
            created_at = Column(DateTime, nullable=False, server_default=func.now())
            updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
        
        class Notice(Base):
            __tablename__ = "notices"
            
            notice_id = Column(BigInteger, primary_key=True, autoincrement=True)
            title = Column(String(100), nullable=False)
            content = Column(Text, nullable=False)
            created_at = Column(DateTime, nullable=False, server_default=func.now())
            updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
        
        class Banner(Base):
            __tablename__ = "banners"
            
            banner_id = Column(BigInteger, primary_key=True, autoincrement=True)
            title = Column(String(100))
            link = Column(Text)
            is_active = Column(Boolean, nullable=False, server_default="1")
            created_at = Column(DateTime, nullable=False, server_default=func.now())
            updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
        
        class Event(Base):
            __tablename__ = "events"
            
            event_id = Column(BigInteger, primary_key=True, autoincrement=True)
            title = Column(String(100))
            category = Column(SQLEnum(EventCategory))
            description = Column(Text)  # event_description -> description
            image_url = Column(Text)
            start_date = Column(DateTime)  # event_date -> start_date
            created_at = Column(DateTime, nullable=False, server_default=func.now())
            updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
        
        print("Creating Support tables (Phase 1, 2 Updated)...")
        print("Note: event_description -> description, event_date -> start_date")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Support tables created successfully!")
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
