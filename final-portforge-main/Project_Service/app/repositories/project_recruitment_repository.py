from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from app.models.project_recruitment import Project as RecruitmentProject, ProjectRecruitmentPosition, ProjectStatus
from app.schemas.project_recruitment import ProjectFilters
from math import ceil


class ProjectRecruitmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, project_data: Dict[str, Any], user_id: int) -> RecruitmentProject:
        """Create a new project with recruitment positions"""
        # Create project
        project = RecruitmentProject(
            title=project_data["title"],
            description=project_data["description"],
            type=project_data["type"],
            method=project_data["method"],
            start_date=project_data["start_date"],
            end_date=project_data["end_date"],
            test_required=project_data["test_required"],
            user_id=str(user_id)  # Convert to string for UUID
        )
        
        self.db.add(project)
        await self.db.flush()  # Get project ID
        
        # Create recruitment positions
        for position_data in project_data["recruitment_positions"]:
            position = ProjectRecruitmentPosition(
                project_id=project.project_id,  # Updated field name
                position_type=position_data["position_type"],  # Updated field name
                required_stacks=position_data["required_stacks"],  # Updated field name
                target_count=position_data["target_count"]  # Updated field name
            )
            self.db.add(position)
        
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project_by_id(self, project_id: int) -> Optional[RecruitmentProject]:
        """Get project by ID with recruitment positions"""
        result = await self.db.execute(
            select(RecruitmentProject)
            .options(selectinload(RecruitmentProject.recruitment_positions))
            .where(RecruitmentProject.project_id == project_id)  # Updated field name
        )
        return result.scalar_one_or_none()

    async def get_projects_with_filters(self, filters: ProjectFilters) -> tuple[List[RecruitmentProject], int]:
        """Get projects with filtering and pagination"""
        query = select(RecruitmentProject).options(selectinload(RecruitmentProject.recruitment_positions))
        
        # Apply filters
        conditions = []
        
        if filters.type:
            conditions.append(RecruitmentProject.type == filters.type)
        
        if filters.status:
            conditions.append(RecruitmentProject.status == filters.status)
        
        if filters.tech_stack:
            # Filter projects that have positions with specific tech stack
            subquery = select(ProjectRecruitmentPosition.project_id).where(
                ProjectRecruitmentPosition.tech_stack.ilike(f"%{filters.tech_stack}%")
            )
            conditions.append(RecruitmentProject.project_id.in_(subquery))  # Updated field name
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(RecruitmentProject.project_id))  # Updated field name
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(RecruitmentProject.created_at.desc())
        query = query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        return projects, total

    async def update_project(self, project_id: int, project_data: Dict[str, Any]) -> Optional[RecruitmentProject]:
        """Update project and its recruitment positions"""
        # Get existing project
        project = await self.get_project_by_id(project_id)
        if not project:
            return None
        
        # Update basic project info
        for key, value in project_data.items():
            if key != "recruitment_positions" and value is not None:
                setattr(project, key, value)
        
        # Handle recruitment positions if provided
        if "recruitment_positions" in project_data and project_data["recruitment_positions"] is not None:
            # Delete existing positions
            await self.db.execute(
                delete(ProjectRecruitmentPosition).where(
                    ProjectRecruitmentPosition.project_id == project_id
                )
            )
            
            # Create new positions
            for position_data in project_data["recruitment_positions"]:
                position = ProjectRecruitmentPosition(
                    project_id=project_id,
                    position_name=position_data["position_name"],
                    tech_stack=position_data["tech_stack"],
                    required_count=position_data["required_count"]
                )
                self.db.add(position)
        
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def increment_views(self, project_id: int) -> bool:
        """Increment project views count"""
        result = await self.db.execute(
            update(RecruitmentProject)
            .where(RecruitmentProject.project_id == project_id)  # Updated field name
            .values(views=RecruitmentProject.views + 1)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update_project_status(self, project_id: int, status: ProjectStatus) -> bool:
        """Update project status"""
        result = await self.db.execute(
            update(RecruitmentProject)
            .where(RecruitmentProject.project_id == project_id)  # Updated field name
            .values(status=status)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def is_project_owner(self, project_id: int, user_id: int) -> bool:
        """Check if user is the project owner"""
        result = await self.db.execute(
            select(RecruitmentProject.project_id)  # Updated field name
            .where(and_(RecruitmentProject.project_id == project_id, RecruitmentProject.user_id == str(user_id)))  # Updated field name and convert to string
        )
        return result.scalar_one_or_none() is not None
    async def delete_project(self, project_id: int) -> bool:
        """Delete project permanently (hard delete)"""
        # First delete related recruitment positions
        await self.db.execute(
            delete(ProjectRecruitmentPosition).where(
                ProjectRecruitmentPosition.project_id == project_id
            )
        )
        
        # Then delete the project
        result = await self.db.execute(
            delete(RecruitmentProject).where(RecruitmentProject.project_id == project_id)  # Updated field name
        )
        await self.db.commit()
        return result.rowcount > 0