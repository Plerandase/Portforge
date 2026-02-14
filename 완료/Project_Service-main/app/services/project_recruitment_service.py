from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime
from app.repositories.project_recruitment_repository import ProjectRecruitmentRepository
from app.schemas.project_recruitment import (
    ProjectCreate, ProjectUpdate, ProjectStatusUpdate, ProjectFilters,
    ProjectDetail, ProjectSummary, ProjectListResponse
)
from app.models.project_recruitment import ProjectStatus
from math import ceil


class ProjectRecruitmentService:
    def __init__(self, project_repo: ProjectRecruitmentRepository):
        self.project_repo = project_repo

    async def create_project(self, project_data: ProjectCreate, user_id: int) -> ProjectDetail:
        """Create a new project with business validation"""
        # Validate dates
        if project_data.start_date >= project_data.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        if project_data.start_date < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be in the past"
            )
        
        # Convert to dict for repository
        project_dict = project_data.model_dump()
        
        # Create project
        project = await self.project_repo.create_project(project_dict, user_id)
        
        return ProjectDetail.model_validate(project)

    async def get_project_detail(self, project_id: int) -> ProjectDetail:
        """Get project detail and increment views"""
        project = await self.project_repo.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Increment views
        await self.project_repo.increment_views(project_id)
        
        return ProjectDetail.model_validate(project)

    async def get_project_list(self, filters: ProjectFilters) -> ProjectListResponse:
        """Get project list with filtering and pagination"""
        projects, total = await self.project_repo.get_projects_with_filters(filters)
        
        # Convert to summary format with recruitment status
        project_summaries = []
        for project in projects:
            total_required = sum(pos.required_count for pos in project.recruitment_positions)
            total_current = sum(pos.current_count for pos in project.recruitment_positions)
            
            summary = ProjectSummary(
                id=project.id,
                title=project.title,
                description=project.description,
                type=project.type,
                method=project.method,
                status=project.status,
                start_date=project.start_date,
                end_date=project.end_date,
                test_required=project.test_required,
                views=project.views,
                user_id=project.user_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                total_required=total_required,
                total_current=total_current,
                recruitment_status=f"{total_current}/{total_required}"
            )
            project_summaries.append(summary)
        
        total_pages = ceil(total / filters.size) if total > 0 else 0
        
        return ProjectListResponse(
            items=project_summaries,
            total=total,
            page=filters.page,
            size=filters.size,
            total_pages=total_pages
        )

    async def update_project(self, project_id: int, project_data: ProjectUpdate, user_id: int) -> ProjectDetail:
        """Update project with authorization check"""
        # Check if user is project owner
        if not await self.project_repo.is_project_owner(project_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owner can update the project"
            )
        
        # Validate dates if provided
        update_dict = project_data.model_dump(exclude_unset=True)
        
        if "start_date" in update_dict and "end_date" in update_dict:
            if update_dict["start_date"] >= update_dict["end_date"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start date must be before end date"
                )
        
        # Update project
        updated_project = await self.project_repo.update_project(project_id, update_dict)
        if not updated_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return ProjectDetail.model_validate(updated_project)

    async def update_project_status(self, project_id: int, status_data: ProjectStatusUpdate, user_id: int) -> dict:
        """Update project status with authorization check"""
        # Check if user is project owner
        if not await self.project_repo.is_project_owner(project_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owner can update project status"
            )
        
        # Update status
        success = await self.project_repo.update_project_status(project_id, status_data.status)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return {"message": f"Project status updated to {status_data.status.value}"}

    async def delete_project(self, project_id: int, user_id: int) -> dict:
        """Soft delete project by setting status to CLOSED"""
        # Check if user is project owner
        if not await self.project_repo.is_project_owner(project_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owner can delete the project"
            )
        
        # Set status to CLOSED (soft delete)
        success = await self.project_repo.update_project_status(project_id, ProjectStatus.CLOSED)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return {"message": "Project has been closed successfully"}