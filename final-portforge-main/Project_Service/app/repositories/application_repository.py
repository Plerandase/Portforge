from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update, delete
from sqlalchemy.orm import selectinload
from app.models.application import Application, ApplicationStatus
from app.models.project_recruitment import RecruitmentProject


class ApplicationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_application(self, project_id: int, user_id: int, application_data: Dict[str, Any]) -> Application:
        """Create a new application"""
        application = Application(
            project_id=project_id,
            user_id=user_id,
            position=application_data["position"],
            motivation=application_data.get("motivation"),
            experience=application_data.get("experience"),
            portfolio=application_data.get("portfolio"),
            available_hours=application_data.get("available_hours"),
            contact=application_data.get("contact"),
            skills=application_data.get("skills"),
            questions=application_data.get("questions"),
            ai_test_score=application_data.get("ai_test_score"),
            ai_test_level=application_data.get("ai_test_level"),
            ai_test_feedback=application_data.get("ai_test_feedback")
        )
        
        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)
        return application

    async def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """Get application by ID"""
        result = await self.db.execute(
            select(Application).where(Application.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_applications_by_project(self, project_id: int) -> List[Application]:
        """Get all applications for a project"""
        result = await self.db.execute(
            select(Application)
            .where(Application.project_id == project_id)
            .order_by(Application.created_at.desc())
        )
        return result.scalars().all()

    async def get_applications_by_user(self, user_id: int) -> List[Application]:
        """Get all applications by a user"""
        result = await self.db.execute(
            select(Application)
            .options(selectinload(Application.project))
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
        )
        return result.scalars().all()

    async def check_existing_application(self, project_id: int, user_id: int) -> Optional[Application]:
        """Check if user already applied to this project"""
        result = await self.db.execute(
            select(Application).where(
                and_(
                    Application.project_id == project_id,
                    Application.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_application_status(self, application_id: int, status: ApplicationStatus) -> bool:
        """Update application status"""
        result = await self.db.execute(
            update(Application)
            .where(Application.id == application_id)
            .values(status=status)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_application_statistics(self, project_id: int) -> Dict[str, int]:
        """Get application statistics for a project"""
        result = await self.db.execute(
            select(
                Application.status,
                func.count(Application.id).label('count')
            )
            .where(Application.project_id == project_id)
            .group_by(Application.status)
        )
        
        stats = {"total": 0, "pending": 0, "accepted": 0, "rejected": 0}
        for status, count in result.fetchall():
            stats["total"] += count
            if status == ApplicationStatus.PENDING:
                stats["pending"] = count
            elif status == ApplicationStatus.ACCEPTED:
                stats["accepted"] = count
            elif status == ApplicationStatus.REJECTED:
                stats["rejected"] = count
        
        return stats

    async def is_project_owner(self, project_id: int, user_id: int) -> bool:
        """Check if user is the project owner"""
        result = await self.db.execute(
            select(RecruitmentProject.id)
            .where(and_(RecruitmentProject.id == project_id, RecruitmentProject.user_id == user_id))
        )
        return result.scalar_one_or_none() is not None