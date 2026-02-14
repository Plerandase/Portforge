"""
Task 모델 정의
팀 내 작업 관리를 위한 모델
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Enum as SQLEnum, func
from app.core.database import Base
from app.models.enums import TaskStatus, TaskPriority


class Task(Base):
    """작업 모델"""
    __tablename__ = "tasks"
    
    task_id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.TODO)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    created_by = Column(String(36), nullable=False)  # UUID as string
    assignee_id = Column(String(36))  # UUID as string
    start_date = Column(DateTime)
    due_date = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Task(task_id={self.task_id}, title='{self.title}', status='{self.status}')>"