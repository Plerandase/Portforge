from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Test(Base):
    __tablename__ = "tests"

    test_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stack_name = Column(String(50), nullable=False)
    question_json = Column(JSON, nullable=False)
    difficulty = Column(String(20), default="초급")
    source_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class TestResult(Base):
    __tablename__ = "test_results"

    result_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    
    project_id = Column(BigInteger, nullable=True)
    application_id = Column(BigInteger, unique=True, nullable=True)
    
    test_type = Column(String(20), default="APPLICATION")
    
    score = Column(BigInteger, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class Portfolio(Base):
    __tablename__ = "portfolios"
    
    portfolio_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    project_id = Column(BigInteger, nullable=False)
    
    title = Column(String(200), default='프로젝트 회고록')
    summary = Column(Text, nullable=True)
    role_description = Column(Text, nullable=True)
    problem_solving = Column(Text, nullable=True)
    tech_stack_usage = Column(Text, nullable=True)
    growth_point = Column(Text, nullable=True)
    external_links = Column(Text, nullable=True)  # 증빙 자료 링크
    
    thumbnail_url = Column(String(1024), nullable=True)
    is_public = Column(Boolean, default=True)
    
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
