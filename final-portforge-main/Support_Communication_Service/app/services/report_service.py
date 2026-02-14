from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ProjectReport, ProjectReportStatus, ProjectReportType


def _status_from_action(action: str) -> ProjectReportStatus:
    action = action.lower()
    if action in ("deleted", "resolved"):
        return ProjectReportStatus.RESOLVED
    if action == "warned":
        return ProjectReportStatus.IN_PROGRESS
    if action == "dismissed":
        return ProjectReportStatus.DISMISSED
    return ProjectReportStatus.PENDING


async def create_report(user_id: str, project_id: int, content: str, type: str = "REPORT") -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        report = ProjectReport(
            user_id=user_id,
            project_id=project_id,
            type=ProjectReportType(type),
            content=content,
            status=ProjectReportStatus.PENDING,
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return {
            "report_id": report.report_id,
            "user_id": report.user_id,
            "project_id": report.project_id,
            "type": report.type.value,
            "content": report.content,
            "status": report.status.value,
            "resolution_note": report.resolution_note,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }


async def list_reports(status: Optional[str] = None) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(ProjectReport).order_by(ProjectReport.created_at.desc())
        if status:
            try:
                stmt = stmt.where(ProjectReport.status == ProjectReportStatus(status))
            except ValueError:
                return []
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "report_id": r.report_id,
                "user_id": r.user_id,
                "project_id": r.project_id,
                "type": r.type.value,
                "content": r.content,
                "status": r.status.value,
                "resolution_note": r.resolution_note,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]


async def update_report(report_id: int, action: str, note: Optional[str] = None) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        report = await session.get(ProjectReport, report_id)
        if not report:
            return None
        report.status = _status_from_action(action)
        # store the action/note for audit
        report.resolution_note = note or action
        await session.commit()
        await session.refresh(report)
        return {
            "report_id": report.report_id,
            "user_id": report.user_id,
            "project_id": report.project_id,
            "type": report.type.value,
            "content": report.content,
            "status": report.status.value,
            "resolution_note": report.resolution_note,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }
