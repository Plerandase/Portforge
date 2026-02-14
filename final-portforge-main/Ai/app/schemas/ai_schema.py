from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Test Schemas ---
# --- Test Schemas ---
class QuestionRequest(BaseModel):
    stack: str
    difficulty: str = "초급"
    count: int = 5
    type: str = "MULTIPLE_CHOICE"  # 'MULTIPLE_CHOICE' or 'SHORT_ANSWER'
    previous_questions: Optional[List[str]] = []

class QuestionItem(BaseModel):
    question: str
    options: Optional[List[str]] = []  # 주관식일 경우 빈 리스트
    answer: str | int  # 객관식(int index) / 주관식(str 모범답안)
    explanation: str
    grading_criteria: Optional[str] = None  # 주관식 채점 기준
    type: Optional[str] = "MULTIPLE_CHOICE"  # 'MULTIPLE_CHOICE' or 'SHORT_ANSWER'

class QuestionResponse(BaseModel):
    questions: List[QuestionItem]

class GradeRequest(BaseModel):
    question: str
    user_answer: str
    model_answer: str
    grading_criteria: Optional[str] = None

class GradeResponse(BaseModel):
    score: int  # 0~100
    feedback: str
    is_correct: bool  # 통과 여부 (예: 70점 이상)

class AnalysisRequest(BaseModel):
    stack: str
    total_questions: int
    correct_count: int
    score: int
    user_id: str
    user_answers: Optional[List[int | str]] = None  # 주관식 답안 지원
    project_id: Optional[int] = None
    application_id: Optional[int] = None

class AnalysisResponse(BaseModel):
    score: int
    level: str
    feedback: str

# --- Portfolio Schemas ---
class PortfolioRequest(BaseModel):
    project_id: int
    user_id: str
    is_team_leader: bool = False

class PortfolioResponse(BaseModel):
    result: dict

class ApplicantData(BaseModel):
    name: str
    position: str
    message: str
    score: Optional[int] = 0
    feedback: Optional[str] = ""

class ApplicantAnalysisRequest(BaseModel):
    applicants: List[ApplicantData]

class ApplicantAnalysisResponse(BaseModel):
    analysis: str

# NOTE: 회의록 관련 스키마는 Team-BE로 이관되었습니다.
