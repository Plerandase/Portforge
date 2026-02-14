from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, Enum, ForeignKey, Date
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProjectType(enum.Enum):
    PROJECT = "PROJECT"
    STUDY = "STUDY"


class ProjectMethod(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MIXED = "MIXED"


class ProjectStatus(enum.Enum):
    RECRUITING = "RECRUITING"
    PROCEEDING = "PROCEEDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class PositionType(enum.Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DB = "DB"
    INFRA = "INFRA"
    DESIGN = "DESIGN"
    ETC = "ETC"
    STUDY_MEMBER = "STUDY_MEMBER"


class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TechStack(enum.Enum):
    # 프론트엔드
    React = "React"
    Vue = "Vue"
    Nextjs = "Nextjs"
    TypeScript = "TypeScript"
    JavaScript = "JavaScript"
    # 백엔드
    Java = "Java"
    Spring = "Spring"
    Nodejs = "Nodejs"
    Python = "Python"
    Django = "Django"
    Flask = "Flask"
    # DB
    MySQL = "MySQL"
    PostgreSQL = "PostgreSQL"
    MongoDB = "MongoDB"
    Redis = "Redis"
    # 인프라
    AWS = "AWS"
    Docker = "Docker"
    Kubernetes = "Kubernetes"


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), nullable=False, comment="팀장 ID")
    type = Column(Enum(ProjectType), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    method = Column(Enum(ProjectMethod), nullable=False, default=ProjectMethod.ONLINE)
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.RECRUITING)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    test_required = Column(Boolean, nullable=False, default=False)
    views = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    recruitment_positions = relationship("ProjectRecruitmentPosition", back_populates="project", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="project", cascade="all, delete-orphan")


class ProjectRecruitmentPosition(Base):
    __tablename__ = "project_recruitment_positions"

    project_id = Column(BigInteger, ForeignKey("projects.project_id"), primary_key=True, nullable=False)
    position_type = Column(Enum(PositionType), primary_key=True, nullable=False)
    required_stacks = Column(Text, nullable=True)
    target_count = Column(Integer, nullable=True)
    current_count = Column(Integer, nullable=False, default=0)
    recruitment_deadline = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="recruitment_positions")


class Application(Base):
    __tablename__ = "applications"

    application_id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey("projects.project_id"), nullable=False)
    user_id = Column(CHAR(36), nullable=False)
    position_type = Column(Enum(PositionType), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="applications")
