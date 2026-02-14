# Project Service 모델 정의
from .project_recruitment import (
    Project, 
    ProjectRecruitmentPosition, 
    ProjectType, 
    ProjectMethod, 
    ProjectStatus,
    PositionType,
    ApplicationStatus,
    Application,
    TechStack
)

# Report 모델 (별도 파일)
try:
    from .report import Report, ReportReason, ReportStatus
except ImportError:
    Report = None
    ReportReason = None
    ReportStatus = None

__all__ = [
    "Project",
    "ProjectRecruitmentPosition",
    "ProjectType",
    "ProjectMethod",
    "ProjectStatus",
    "PositionType",
    "ApplicationStatus",
    "Application",
    "TechStack",
    "Report",
    "ReportReason",
    "ReportStatus",
]