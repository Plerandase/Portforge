from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ReportReason(enum.Enum):
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SPAM = "spam"
    FRAUD = "fraud"
    COPYRIGHT_VIOLATION = "copyright_violation"
    OTHER = "other"


class ReportStatus(enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(BigInteger, ForeignKey("projects.project_id"), nullable=False)
    reporter_id = Column(String(36), nullable=False)  # User ID
    reason = Column(Enum(ReportReason), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    reported_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    # project = relationship("Project", back_populates="reports")