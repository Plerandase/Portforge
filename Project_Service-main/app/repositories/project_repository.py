from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.project import Project, ProjectStatus
from app.models.application import Application, ApplicationStatus
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project entity with business-specific queries"""
    
    def __init__(self, db: Session):
        super().__init__(Project, db)
    
    def get_all_with_user_filter(self, user_id: int) -> List[Project]:
        """Get all projects with user-based filtering (business rule from service)"""
        # Business rule: show active projects to all users, but show all projects to owners
        result = self.db.execute(
            select(Project).where(
                or_(
                    Project.created_by == user_id,  # User's own projects (any status)
                    Project.status == ProjectStatus.ACTIVE  # Active projects for all users
                )
            ).order_by(Project.created_at.desc())
        )
        return result.scalars().all()
    
    def get_by_id_with_details(self, project_id: int) -> Optional[Project]:
        """Get project by ID with related data loaded"""
        result = self.db.execute(
            select(Project)
            .options(selectinload(Project.applications))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    def create_project(self, project_data: Dict[str, Any], user_id: int) -> Project:
        """Create new project with user as owner"""
        project = Project(
            title=project_data["title"],
            description=project_data["description"],
            budget=project_data.get("budget"),
            deadline=project_data.get("deadline"),
            created_by=user_id,
            status=ProjectStatus.ACTIVE
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project
    
    def is_owned_by_user(self, project_id: int, user_id: int) -> bool:
        """Check if project is owned by user"""
        result = self.db.execute(
            select(Project.id).where(
                and_(
                    Project.id == project_id,
                    Project.created_by == user_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    def exists_and_active(self, project_id: int) -> bool:
        """Check if project exists and is active"""
        result = self.db.execute(
            select(Project.id).where(
                and_(
                    Project.id == project_id,
                    Project.status == ProjectStatus.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none() is not None