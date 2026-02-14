from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from datetime import datetime
from app.repositories.project_repository import ProjectRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.report_repository import ReportRepository
from app.models.application import ApplicationStatus
from app.models.report import ReportReason


class ProjectService:
    """Service layer for project-related business logic"""
    
    def __init__(self, project_repo: ProjectRepository, application_repo: ApplicationRepository, report_repo: ReportRepository):
        self.project_repo = project_repo
        self.application_repo = application_repo
        self.report_repo = report_repo
    
    def get_all_projects(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all projects with business rules applied"""
        try:
            projects = self.project_repo.get_all_with_user_filter(user_id)
            
            # Convert to dict format for API response
            return [
                {
                    "id": project.id,
                    "title": project.title,
                    "description": project.description,
                    "status": project.status.value,
                    "created_by": project.created_by,
                    "created_at": project.created_at.isoformat() + "Z",
                    "budget": float(project.budget) if project.budget else None,
                    "deadline": project.deadline.isoformat() + "Z" if project.deadline else None
                }
                for project in projects
            ]
        except Exception as e:
            # Return empty list if there's an error (for now)
            return []
    
    def get_project_by_id(self, project_id: int, user_id: int) -> Dict[str, Any]:
        """Get project by ID with business rules applied"""
        if project_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID"
            )
        
        try:
            project = self.project_repo.get_by_id_with_details(project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )
            
            # Convert to dict format
            result = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "status": project.status.value,
                "created_by": project.created_by,
                "created_at": project.created_at.isoformat() + "Z",
                "budget": float(project.budget) if project.budget else None,
                "deadline": project.deadline.isoformat() + "Z" if project.deadline else None
            }
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving project"
            )
    
    def create_project(self, project_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create new project with business validation"""
        title = project_data.get("title", "").strip()
        description = project_data.get("description", "").strip()
        
        # Basic validation
        if not title or len(title) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title must be at least 3 characters"
            )
        
        if not description or len(description) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description must be at least 10 characters"
            )
        
        try:
            # Create project using repository
            project = self.project_repo.create_project(project_data, user_id)
            
            return {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "status": project.status.value,
                "created_by": project.created_by,
                "created_at": project.created_at.isoformat() + "Z",
                "budget": float(project.budget) if project.budget else None,
                "deadline": project.deadline.isoformat() + "Z" if project.deadline else None
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating project"
            )
    
    def apply_to_project(self, project_id: int, application_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Apply to project - simplified version"""
        return {"message": "Application feature not implemented yet"}
    
    def update_application_status(self, project_id: int, application_id: int, status_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Update application status - simplified version"""
        return {"message": "Application status update not implemented yet"}
    
    def report_project(self, project_id: int, report_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        프로젝트 신고
        
        Args:
            project_id: 신고할 프로젝트 ID
            report_data: 신고 데이터 (reason, description)
            user_id: 신고자 ID
            
        Returns:
            신고 결과 정보
        """
        from app.models.report import Report, ReportReason, ReportStatus
        from sqlalchemy import and_
        
        # 1. Validation - reason 필수
        reason = report_data.get("reason")
        description = report_data.get("description", "").strip()
        
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="신고 사유(reason)는 필수입니다."
            )
        
        # 2. reason 유효성 검사
        valid_reasons = [r.value for r in ReportReason]
        if reason not in valid_reasons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 신고 사유입니다. 가능한 값: {valid_reasons}"
            )
        
        if not description or len(description) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="신고 내용(description)은 10자 이상이어야 합니다."
            )
        
        try:
            # 3. 프로젝트 존재 확인
            project = self.project_repo.get_by_id(project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="프로젝트를 찾을 수 없습니다."
                )
            
            # 4. 자기 프로젝트 신고 방지
            if project.created_by == user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="자신의 프로젝트는 신고할 수 없습니다."
                )
            
            # 5. 중복 신고 방지 (sync 방식)
            from sqlalchemy import select
            existing_report = self.report_repo.db.execute(
                select(Report).where(
                    and_(
                        Report.project_id == project_id,
                        Report.reporter_id == user_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing_report:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 이 프로젝트를 신고하셨습니다."
                )
            
            # 6. 신고 저장
            report = Report(
                project_id=project_id,
                reporter_id=user_id,
                reason=ReportReason(reason),
                description=description,
                status=ReportStatus.PENDING
            )
            self.report_repo.db.add(report)
            self.report_repo.db.commit()
            self.report_repo.db.refresh(report)
            
            return {
                "success": True,
                "message": "프로젝트 신고가 접수되었습니다.",
                "report": {
                    "id": report.id,
                    "project_id": report.project_id,
                    "reason": report.reason.value,
                    "description": report.description,
                    "status": report.status.value,
                    "reported_at": report.reported_at.isoformat() + "Z"
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.report_repo.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"신고 처리 중 오류가 발생했습니다: {str(e)}"
            )