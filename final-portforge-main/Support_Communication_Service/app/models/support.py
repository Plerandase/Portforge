from enum import Enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    String,
    Text,
    func,
)
from app.core.database import Base


class ProjectReportType(str, Enum):
    REPORT = "REPORT"
    INQUIRY = "INQUIRY"
    BUG = "BUG"


class ProjectReportStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class EventCategory(str, Enum):
    CONTEST = "CONTEST"
    HACKATHON = "HACKATHON"


class ProjectReport(Base):
    __tablename__ = "project_reports"

    report_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)
    project_id = Column(BigInteger, nullable=False, index=True)
    type = Column(SAEnum(ProjectReportType), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(SAEnum(ProjectReportStatus), nullable=False, server_default=ProjectReportStatus.PENDING.value)
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
    category = Column(SAEnum(EventCategory))
    description = Column(Text)
    image_url = Column(Text)
    start_date = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
