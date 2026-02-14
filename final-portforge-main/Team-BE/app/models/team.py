from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, Enum as SQLEnum, Text, Integer, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import TeamRole, StackCategory, MeetingStatus, ReportType


class Team(Base):
    __tablename__ = "teams"
    
    team_id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    meeting_sessions = relationship("MeetingSession", back_populates="team", cascade="all, delete-orphan")
    generated_reports = relationship("GeneratedReport", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"
    
    team_id = Column(BigInteger, ForeignKey("teams.team_id"), primary_key=True)
    user_id = Column(String(36), primary_key=True)
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER)
    position_type = Column(SQLEnum(StackCategory), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    team = relationship("Team", back_populates="members")


class SharedFile(Base):
    __tablename__ = "shared_files"
    
    file_id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, nullable=False)
    team_id = Column(BigInteger, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    file_url = Column(String(1024), nullable=False)
    s3_key = Column(String(1024), nullable=False)
    uploaded_by = Column(String(36), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class Invitation(Base):
    __tablename__ = "invitations"
    
    invitation_id = Column(String(36), primary_key=True)
    project_id = Column(BigInteger, nullable=False)
    invitation_code = Column(String(20), unique=True, nullable=False)
    invitation_link = Column(String(1024), nullable=False)
    invited_by = Column(String(36), nullable=False)
    position_type = Column(SQLEnum(StackCategory), nullable=False)
    message = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by = Column(String(36))
    used_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"
    
    session_id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id = Column(BigInteger, ForeignKey("teams.team_id"), nullable=False)
    project_id = Column(BigInteger, nullable=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(MeetingStatus), default=MeetingStatus.IN_PROGRESS)
    generated_report_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    team = relationship("Team", back_populates="meeting_sessions")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    
    report_id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id = Column(BigInteger, ForeignKey("teams.team_id"), nullable=False)
    project_id = Column(BigInteger, nullable=True)
    created_by = Column(String(36), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, COMPLETED, FAILED
    model_id = Column(String(100), nullable=True)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    s3_key = Column(String(1024), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    team = relationship("Team", back_populates="generated_reports")