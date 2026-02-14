from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.models.report import Report, ReportReason, ReportStatus
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    """Repository for Report entity with business-specific queries"""
    
    def __init__(self, db: Session):
        super().__init__(Report, db)
    
    async def create_report(self, project_id: int, report_data: Dict[str, Any], user_id: int) -> Report:
        """Create new report"""
        report = Report(
            project_id=project_id,
            reporter_id=user_id,
            reason=ReportReason(report_data["reason"]),
            description=report_data["description"],
            status=ReportStatus.PENDING
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
    
    async def has_user_reported(self, project_id: int, user_id: int) -> bool:
        """Check if user has already reported this project"""
        result = await self.db.execute(
            select(Report.id).where(
                and_(
                    Report.project_id == project_id,
                    Report.reporter_id == user_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_reports_by_project(self, project_id: int) -> List[Report]:
        """Get all reports for a project"""
        result = await self.db.execute(
            select(Report).where(Report.project_id == project_id)
            .order_by(Report.reported_at.desc())
        )
        return result.scalars().all()