from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.deps import get_current_user, get_db
from app.services.project_service import ProjectService
from app.repositories.project_repository import ProjectRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.report_repository import ReportRepository

router = APIRouter(prefix="/projects")


@router.get("", response_model=List[Dict[str, Any]])
def get_projects(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all projects"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.get_all_projects(current_user.get("id"))


@router.get("/{project_id}", response_model=Dict[str, Any])
def get_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by ID"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.get_project_by_id(project_id, current_user.get("id"))


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.create_project(project_data, current_user.get("id"))


@router.post("/{project_id}/apply", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def apply_to_project(
    project_id: int,
    application_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply to a project"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.apply_to_project(project_id, application_data, current_user.get("id"))


@router.patch("/{project_id}/applicants/{application_id}", response_model=Dict[str, Any])
def update_application_status(
    project_id: int,
    application_id: int,
    status_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application status (approve/reject)"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.update_application_status(
        project_id, application_id, status_data, current_user.get("id")
    )


@router.post("/{project_id}/report", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def report_project(
    project_id: int,
    report_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Report a project"""
    project_service = ProjectService(
        ProjectRepository(db),
        ApplicationRepository(db),
        ReportRepository(db)
    )
    return project_service.report_project(project_id, report_data, current_user.get("id"))