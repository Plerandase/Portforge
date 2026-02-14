from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("recruitment_projects.id"), nullable=False)
    user_id = Column(Integer, nullable=False)  # 지원자 ID
    position = Column(String(100), nullable=False)  # 지원 포지션
    message = Column(Text, nullable=True)  # 지원자 메시지
    
    # 지원서 상세 정보
    motivation = Column(Text, nullable=True)  # 지원 동기
    experience = Column(Text, nullable=True)  # 경력 및 경험
    portfolio = Column(String(500), nullable=True)  # 포트폴리오 URL
    available_hours = Column(String(100), nullable=True)  # 참여 가능 시간
    contact = Column(String(200), nullable=True)  # 연락처
    skills = Column(Text, nullable=True)  # 보유 기술
    questions = Column(Text, nullable=True)  # 질문사항
    
    # AI 테스트 결과
    ai_test_score = Column(Integer, nullable=True)  # AI 테스트 점수
    ai_test_level = Column(String(50), nullable=True)  # AI 테스트 수준
    ai_test_feedback = Column(Text, nullable=True)  # AI 테스트 피드백
    
    # 상태 및 메타데이터
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.PENDING)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("RecruitmentProject", back_populates="applications")