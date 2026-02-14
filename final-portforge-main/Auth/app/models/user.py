# app/models/user.py - ERD 반영 User 모델
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, Enum as SQLEnum, BigInteger, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.session import Base
from app.models.enums import UserRole, StackCategory, TechStack

class User(Base):
    __tablename__ = "users"
    
    # [ERD 반영] user_id는 Cognito sub (UUID 문자열)
    user_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, nullable=False, comment='관리/검색용 이메일 스냅샷')
    nickname = Column(String(20), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    profile_image_url = Column(Text, nullable=True)
    liked_project_ids = Column(JSON, nullable=True, comment='Array: [1, 20, 55]')
    test_count = Column(Integer, default=5)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정 (cascade 설정으로 유저 삭제 시 관련 데이터도 함께 삭제)
    stacks = relationship(
        "UserStack", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="selectin"  # 비동기 환경에서 연관 데이터를 즉시 가져오도록 설정
    )

    @property
    def myStacks(self):
        """프론트엔드용 스택 문자열 리스트 반환"""
        return [str(s.stack_name) for s in self.stacks]

class UserStack(Base):
    __tablename__ = "user_stacks"
    
    stack_id = Column(BigInteger, primary_key=True, autoincrement=True, comment='🔑 PK')
    user_id = Column(CHAR(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    position_type = Column(SQLEnum(StackCategory), nullable=False)
    stack_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="stacks")
