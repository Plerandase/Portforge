from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from app.models.team import Team, TeamMember, MeetingSession, GeneratedReport, Task, SharedFile, Invitation
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamMemberCreate, TeamMemberUpdate,
    MeetingSessionCreate, MeetingSessionUpdate,
    GeneratedReportCreate, TaskCreate, TaskUpdate, SharedFileCreate,
    InvitationCreate
)
import uuid
import secrets

class TeamService:
    
    @staticmethod
    async def create_team(db: AsyncSession, team_data: TeamCreate) -> Team:
        """새 팀 생성"""
        team = Team(**team_data.dict())
        db.add(team)
        await db.commit()
        await db.refresh(team)
        return team
    
    @staticmethod
    async def get_team_by_id(db: AsyncSession, team_id: int) -> Optional[Team]:
        """팀 ID로 팀 조회"""
        result = await db.execute(
            select(Team).where(Team.team_id == team_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_team_by_project_id(db: AsyncSession, project_id: int) -> Optional[Team]:
        """프로젝트 ID로 팀 조회"""
        result = await db.execute(
            select(Team).where(Team.project_id == project_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_team(db: AsyncSession, team_id: int, team_data: TeamUpdate) -> Optional[Team]:
        """팀 정보 수정"""
        team = await TeamService.get_team_by_id(db, team_id)
        if not team:
            return None
        
        for field, value in team_data.dict(exclude_unset=True).items():
            setattr(team, field, value)
        
        await db.commit()
        await db.refresh(team)
        return team
    
    @staticmethod
    async def delete_team(db: AsyncSession, team_id: int) -> bool:
        """팀 삭제"""
        team = await TeamService.get_team_by_id(db, team_id)
        if not team:
            return False
        
        await db.delete(team)
        await db.commit()
        return True

class TeamMemberService:
    
    @staticmethod
    async def add_member(db: AsyncSession, member_data: TeamMemberCreate) -> TeamMember:
        """팀 멤버 추가"""
        member = TeamMember(**member_data.dict())
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member
    
    @staticmethod
    async def get_team_members(db: AsyncSession, team_id: int) -> List[TeamMember]:
        """팀의 모든 멤버 조회"""
        result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_member(db: AsyncSession, team_id: int, user_id: str) -> Optional[TeamMember]:
        """특정 팀 멤버 조회"""
        result = await db.execute(
            select(TeamMember).where(
                and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_member(db: AsyncSession, team_id: int, user_id: str, member_data: TeamMemberUpdate) -> Optional[TeamMember]:
        """팀 멤버 정보 수정"""
        member = await TeamMemberService.get_member(db, team_id, user_id)
        if not member:
            return None
        
        for field, value in member_data.dict(exclude_unset=True).items():
            setattr(member, field, value)
        
        await db.commit()
        await db.refresh(member)
        return member
    
    @staticmethod
    async def remove_member(db: AsyncSession, team_id: int, user_id: str) -> bool:
        """팀 멤버 제거"""
        member = await TeamMemberService.get_member(db, team_id, user_id)
        if not member:
            return False
        
        await db.delete(member)
        await db.commit()
        return True

class MeetingService:
    
    @staticmethod
    async def create_session(db: AsyncSession, session_data: MeetingSessionCreate) -> MeetingSession:
        """회의 세션 생성"""
        session = MeetingSession(**session_data.dict())
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def get_team_sessions(db: AsyncSession, team_id: int, limit: int = 10) -> List[MeetingSession]:
        """팀의 회의 세션 목록 조회"""
        result = await db.execute(
            select(MeetingSession)
            .where(MeetingSession.team_id == team_id)
            .order_by(MeetingSession.start_time.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_session(db: AsyncSession, session_id: int, session_data: MeetingSessionUpdate) -> Optional[MeetingSession]:
        """회의 세션 수정"""
        result = await db.execute(
            select(MeetingSession).where(MeetingSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        for field, value in session_data.dict(exclude_unset=True).items():
            setattr(session, field, value)
        
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def create_report(db: AsyncSession, report_data: GeneratedReportCreate) -> GeneratedReport:
        """AI 생성 리포트 생성"""
        report = GeneratedReport(**report_data.dict())
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report
    
    @staticmethod
    async def get_team_reports(db: AsyncSession, team_id: int, limit: int = 10) -> List[GeneratedReport]:
        """팀의 생성된 리포트 목록 조회"""
        result = await db.execute(
            select(GeneratedReport)
            .where(GeneratedReport.team_id == team_id)
            .order_by(GeneratedReport.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

class TaskService:
    
    @staticmethod
    async def create_task(db: AsyncSession, project_id: int, task_data: TaskCreate) -> Task:
        """새 태스크 생성"""
        task = Task(project_id=project_id, **task_data.dict())
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task
    
    @staticmethod
    async def get_project_tasks(db: AsyncSession, project_id: int, status: Optional[str] = None) -> List[Task]:
        """프로젝트의 태스크 목록 조회"""
        query = select(Task).where(Task.project_id == project_id)
        if status:
            query = query.where(Task.status == status)
        
        result = await db.execute(query.order_by(Task.created_at.desc()))
        return result.scalars().all()
    
    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[Task]:
        """태스크 ID로 조회"""
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_task(db: AsyncSession, task_id: int, task_data: TaskUpdate) -> Optional[Task]:
        """태스크 수정"""
        task = await TaskService.get_task_by_id(db, task_id)
        if not task:
            return None
        
        for field, value in task_data.dict(exclude_unset=True).items():
            setattr(task, field, value)
        
        task.updated_at = datetime.now()
        await db.commit()
        await db.refresh(task)
        return task
    
    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int) -> bool:
        """태스크 삭제"""
        task = await TaskService.get_task_by_id(db, task_id)
        if not task:
            return False
        
        await db.delete(task)
        await db.commit()
        return True

class FileService:
    
    @staticmethod
    async def create_shared_file(db: AsyncSession, project_id: int, file_data: SharedFileCreate) -> SharedFile:
        """공유 파일 생성"""
        shared_file = SharedFile(project_id=project_id, **file_data.dict())
        db.add(shared_file)
        await db.commit()
        await db.refresh(shared_file)
        return shared_file
    
    @staticmethod
    async def get_project_files(db: AsyncSession, project_id: int, file_type: Optional[str] = None) -> List[SharedFile]:
        """프로젝트의 공유 파일 목록 조회"""
        query = select(SharedFile).where(SharedFile.project_id == project_id)
        if file_type:
            query = query.where(SharedFile.file_type == file_type)
        
        result = await db.execute(query.order_by(SharedFile.created_at.desc()))
        return result.scalars().all()
    
    @staticmethod
    async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[SharedFile]:
        """파일 ID로 조회"""
        result = await db.execute(select(SharedFile).where(SharedFile.file_id == file_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_file(db: AsyncSession, file_id: int) -> bool:
        """파일 삭제"""
        file = await FileService.get_file_by_id(db, file_id)
        if not file:
            return False
        
        await db.delete(file)
        await db.commit()
        return True

class InvitationService:
    
    @staticmethod
    async def create_invitation(db: AsyncSession, project_id: int, invitation_data: InvitationCreate) -> Invitation:
        """팀 초대 생성"""
        invitation_id = str(uuid.uuid4())
        invitation_code = secrets.token_urlsafe(8)
        invitation_link = f"https://your-domain.com/join/{invitation_code}"
        expires_at = datetime.now() + timedelta(hours=invitation_data.expires_in_hours)
        
        invitation = Invitation(
            invitation_id=invitation_id,
            project_id=project_id,
            invitation_code=invitation_code,
            invitation_link=invitation_link,
            invited_by=invitation_data.invited_by,
            position_type=invitation_data.position_type,
            message=invitation_data.message,
            expires_at=expires_at
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        return invitation
    
    @staticmethod
    async def get_project_invitations(db: AsyncSession, project_id: int, active_only: bool = True) -> List[Invitation]:
        """프로젝트의 초대 목록 조회"""
        query = select(Invitation).where(Invitation.project_id == project_id)
        if active_only:
            query = query.where(
                and_(
                    Invitation.is_used == 0,
                    Invitation.expires_at > datetime.now()
                )
            )
        
        result = await db.execute(query.order_by(Invitation.created_at.desc()))
        return result.scalars().all()
    
    @staticmethod
    async def get_invitation_by_code(db: AsyncSession, invitation_code: str) -> Optional[Invitation]:
        """초대 코드로 조회"""
        result = await db.execute(
            select(Invitation).where(Invitation.invitation_code == invitation_code)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def accept_invitation(db: AsyncSession, invitation_code: str, user_id: str) -> Optional[Invitation]:
        """초대 수락"""
        invitation = await InvitationService.get_invitation_by_code(db, invitation_code)
        if not invitation or invitation.is_used or invitation.expires_at < datetime.now():
            return None
        
        invitation.is_used = 1
        invitation.used_by = user_id
        invitation.used_at = datetime.now()
        
        await db.commit()
        await db.refresh(invitation)
        return invitation
    
    @staticmethod
    async def cancel_invitation(db: AsyncSession, invitation_id: str) -> bool:
        """초대 취소"""
        result = await db.execute(
            select(Invitation).where(Invitation.invitation_id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            return False
        
        await db.delete(invitation)
        await db.commit()
        return True