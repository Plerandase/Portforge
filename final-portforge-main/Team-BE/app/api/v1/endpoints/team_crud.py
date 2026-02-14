"""
Team Service - 팀 CRUD API
ERD 기반 MSA 분리: 팀/팀원/태스크/파일공유 관리
Project Service에서 호출되는 API 포함
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from datetime import datetime
import logging
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.team import Team, TeamMember, SharedFile, Invitation
from app.models.task import Task
from app.models.enums import TeamRole, StackCategory

logger = logging.getLogger(__name__)

router = APIRouter()

# =====================================================
# 헬퍼 함수
# =====================================================
def convert_position_type(position_str: str) -> StackCategory:
    """한글/영어 포지션명을 StackCategory로 변환"""
    mapping = {
        "프론트엔드": StackCategory.FRONTEND,
        "FRONTEND": StackCategory.FRONTEND,
        "백엔드": StackCategory.BACKEND,
        "BACKEND": StackCategory.BACKEND,
        "디자인": StackCategory.DESIGN,
        "DESIGN": StackCategory.DESIGN,
        "DB": StackCategory.DB,
        "DATABASE": StackCategory.DB,
        "인프라": StackCategory.INFRA,
        "INFRA": StackCategory.INFRA,
        "기타": StackCategory.ETC,
        "ETC": StackCategory.ETC,
        "스터디원": StackCategory.STUDY_MEMBER,
        "STUDY_MEMBER": StackCategory.STUDY_MEMBER,
    }
    return mapping.get(position_str.upper() if position_str else "ETC", StackCategory.ETC)

# =====================================================
# 1. 팀 생성 (Project Service에서 호출)
# =====================================================
@router.post("")
async def create_team(team_data: dict, db: AsyncSession = Depends(get_db)):
    """팀 생성 - Project Service에서 프로젝트 생성 시 호출"""
    try:
        project_id = team_data.get("project_id")
        team_name = team_data.get("name", f"프로젝트 {project_id} 개발팀")
        leader_id = team_data.get("leader_id")
        leader_position = team_data.get("leader_position", "백엔드")
        
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id는 필수입니다.")
        
        # 이미 팀이 있는지 확인
        existing_result = await db.execute(select(Team).where(Team.project_id == project_id))
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"프로젝트 {project_id}에 이미 팀이 존재합니다.")
            return {
                "status": "success",
                "message": "이미 팀이 존재합니다.",
                "data": {"team_id": existing.team_id, "project_id": project_id}
            }
        
        # 팀 생성
        new_team = Team(
            project_id=project_id,
            name=team_name,
            s3_key=f"teams/{project_id}/shared_files/",
        )
        
        db.add(new_team)
        await db.flush()
        team_id = new_team.team_id
        logger.info(f"팀 생성됨: {team_id} (프로젝트 {project_id})")
        
        # 팀장을 팀 멤버로 추가
        if leader_id:
            leader_position_enum = convert_position_type(leader_position)
            team_leader = TeamMember(
                team_id=team_id,
                user_id=leader_id,
                role=TeamRole.LEADER,
                position_type=leader_position_enum,
            )
            db.add(team_leader)
            logger.info(f"팀장 추가됨: {leader_id}")
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "팀이 성공적으로 생성되었습니다.",
            "data": {
                "team_id": team_id,
                "project_id": project_id,
                "name": team_name,
                "s3_key": f"teams/{project_id}/shared_files/",
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"팀 생성 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 생성 실패: {str(e)}")

# =====================================================
# 2. 팀 멤버 추가 (Project Service에서 지원 승인 시 호출)
# =====================================================
@router.post("/members")
async def add_team_member(member_data: dict, db: AsyncSession = Depends(get_db)):
    """팀 멤버 추가 - Project Service에서 지원 승인 시 호출"""
    try:
        project_id = member_data.get("project_id")
        user_id = member_data.get("user_id")
        position_type_str = member_data.get("position_type", "BACKEND")
        role_str = member_data.get("role", "MEMBER")
        
        if not project_id or not user_id:
            raise HTTPException(status_code=400, detail="project_id와 user_id는 필수입니다.")
        
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다.")
        
        # 이미 멤버인지 확인
        existing_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.team_id,
                TeamMember.user_id == user_id
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            return {
                "status": "success",
                "message": "이미 팀 멤버입니다.",
                "data": {"team_id": team.team_id, "user_id": user_id}
            }
        
        # 멤버 추가
        position_type = convert_position_type(position_type_str)
        role = TeamRole.LEADER if role_str == "LEADER" else TeamRole.MEMBER
        
        new_member = TeamMember(
            team_id=team.team_id,
            user_id=user_id,
            role=role,
            position_type=position_type,
        )
        
        db.add(new_member)
        await db.commit()
        
        logger.info(f"팀 멤버 추가됨: {user_id} -> 팀 {team.team_id}")
        
        return {
            "status": "success",
            "message": "팀 멤버가 추가되었습니다.",
            "data": {
                "team_id": team.team_id,
                "user_id": user_id,
                "role": role.value,
                "position_type": position_type.value,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"팀 멤버 추가 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 멤버 추가 실패: {str(e)}")

# =====================================================
# 3. 팀 정보 조회 (프로젝트 ID로)
# =====================================================
@router.get("/by-project/{project_id}")
async def get_team_by_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트 ID로 팀 정보 조회"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            return {
                "status": "error",
                "message": "팀을 찾을 수 없습니다.",
                "data": None
            }
        
        # 팀 멤버 조회
        members_result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team.team_id)
        )
        members = members_result.scalars().all()
        
        members_data = []
        for member in members:
            members_data.append({
                "user_id": member.user_id,
                "role": member.role.value if member.role else "MEMBER",
                "position_type": member.position_type.value if member.position_type else "UNKNOWN",
                "updated_at": member.updated_at.isoformat() if member.updated_at else None,
            })
        
        return {
            "status": "success",
            "data": {
                "team_id": team.team_id,
                "project_id": team.project_id,
                "name": team.name,
                "s3_key": team.s3_key,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "members": members_data,
            }
        }
        
    except Exception as e:
        logger.error(f"팀 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"팀 조회 실패: {str(e)}")

# =====================================================
# 4. 팀 대시보드 통계 조회
# =====================================================
@router.get("/{project_id}/stats")
async def get_team_stats(project_id: int, db: AsyncSession = Depends(get_db)):
    """팀 대시보드 정보 조회 (팀스페이스용)"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            # 팀이 없으면 기본 데이터 반환
            return {
                "team_id": project_id,
                "project_id": project_id,
                "name": f"프로젝트 {project_id} 팀",
                "members": [],
                "stats": {
                    "total_members": 0,
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "total_files": 0,
                }
            }
        
        # 팀 멤버 조회
        members_result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team.team_id)
        )
        members = members_result.scalars().all()
        
        members_data = []
        for member in members:
            members_data.append({
                "user_id": member.user_id,
                "role": member.role.value if member.role else "MEMBER",
                "position_type": member.position_type.value if member.position_type else "UNKNOWN",
            })
        
        # 태스크 통계
        tasks_result = await db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        tasks = tasks_result.scalars().all()
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "DONE"])
        
        # 파일 통계
        files_result = await db.execute(
            select(SharedFile).where(SharedFile.team_id == team.team_id)
        )
        files = files_result.scalars().all()
        
        return {
            "team_id": team.team_id,
            "project_id": project_id,
            "name": team.name,
            "members": members_data,
            "stats": {
                "total_members": len(members),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "total_files": len(files),
            }
        }
        
    except Exception as e:
        logger.error(f"팀 통계 조회 실패: {str(e)}")
        return {
            "team_id": project_id,
            "project_id": project_id,
            "name": f"프로젝트 {project_id} 팀",
            "members": [],
            "stats": {"total_members": 0, "total_tasks": 0, "completed_tasks": 0, "total_files": 0}
        }

# =====================================================
# 5. 팀 삭제 (Project Service에서 프로젝트 삭제 시 호출)
# =====================================================
@router.delete("/by-project/{project_id}")
async def delete_team_by_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트 삭제 시 팀 삭제"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if team:
            from app.services.file_service import FileService

            # Delete shared files from S3 first
            files_result = await db.execute(select(SharedFile).where(SharedFile.team_id == team.team_id))
            files = files_result.scalars().all()
            file_service = FileService()
            for f in files:
                if f.s3_key:
                    try:
                        file_service.delete_file(f.s3_key)
                    except Exception as e:
                        logger.warning(f"S3 delete failed: {f.s3_key} ({e})")

            # ?? ??? ?? (cascade? ????? ??? ?????)
            await db.execute(text(f"DELETE FROM team_members WHERE team_id = {team.team_id}"))
            await db.execute(text(f"DELETE FROM tasks WHERE project_id = {project_id}"))
            await db.execute(text(f"DELETE FROM shared_files WHERE team_id = {team.team_id}"))
            await db.delete(team)
            await db.commit()

            logger.info(f"? ???: ???? {project_id}")
        
        return {"status": "success", "message": "팀이 삭제되었습니다."}
        
    except Exception as e:
        logger.error(f"팀 삭제 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 삭제 실패: {str(e)}")

# =====================================================
# 6. 칸반 태스크 목록 조회
# =====================================================
@router.get("/{project_id}/tasks")
async def get_tasks(project_id: int, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """칸반 보드 태스크 조회"""
    try:
        query = select(Task).where(Task.project_id == project_id)
        
        if status:
            query = query.where(Task.status == status)
        
        query = query.order_by(Task.created_at.desc())
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "status": task.status or "TODO",
                "priority": task.priority or "MEDIUM",
                "assignee_id": task.assignee_id,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            })
        
        return tasks_data
        
    except Exception as e:
        logger.error(f"태스크 조회 실패: {str(e)}")
        return []

# =====================================================
# 7. 태스크 생성
# =====================================================
@router.post("/{project_id}/tasks")
async def create_task(project_id: int, task_data: dict, db: AsyncSession = Depends(get_db)):
    """태스크 생성"""
    try:
        new_task = Task(
            project_id=project_id,
            title=task_data.get("title", "새 태스크"),
            description=task_data.get("description", ""),
            status=task_data.get("status", "TODO"),
            priority=task_data.get("priority", "MEDIUM"),
            assignee_id=task_data.get("assignee_id"),
            created_by=task_data.get("user_id", "unknown"),
            due_date=datetime.strptime(task_data["due_date"], "%Y-%m-%d") if task_data.get("due_date") else None,
        )
        
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        
        return {
            "status": "success",
            "message": "태스크가 생성되었습니다.",
            "data": {
                "task_id": new_task.task_id,
                "title": new_task.title,
                "status": new_task.status,
            }
        }
        
    except Exception as e:
        logger.error(f"태스크 생성 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"태스크 생성 실패: {str(e)}")

# =====================================================
# 8. 태스크 수정
# =====================================================
@router.patch("/{project_id}/tasks/{task_id}")
async def update_task(project_id: int, task_id: int, task_data: dict, db: AsyncSession = Depends(get_db)):
    """태스크 수정"""
    try:
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
        
        # 수정 가능한 필드
        if "title" in task_data:
            task.title = task_data["title"]
        if "description" in task_data:
            task.description = task_data["description"]
        if "status" in task_data:
            task.status = task_data["status"]
        if "priority" in task_data:
            task.priority = task_data["priority"]
        if "assignee_id" in task_data:
            task.assignee_id = task_data["assignee_id"]
        if "due_date" in task_data and task_data["due_date"]:
            task.due_date = datetime.strptime(task_data["due_date"], "%Y-%m-%d")
        
        task.updated_at = datetime.now()
        await db.commit()
        
        return {"status": "success", "message": "태스크가 수정되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태스크 수정 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"태스크 수정 실패: {str(e)}")

# =====================================================
# 9. 파일 목록 조회
# =====================================================
@router.get("/{project_id}/files")
async def get_files(project_id: int, db: AsyncSession = Depends(get_db)):
    """팀 파일 목록 조회"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            return []
        
        files_result = await db.execute(
            select(SharedFile)
            .where(SharedFile.team_id == team.team_id)
            .order_by(SharedFile.created_at.desc())
        )
        files = files_result.scalars().all()
        
        files_data = []
        for file in files:
            files_data.append({
                "file_id": file.file_id,
                "file_name": file.file_name,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "uploaded_by": file.uploaded_by,
                "description": file.description,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "s3_key": file.s3_key,
            })
        
        return files_data
        
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {str(e)}")
        return []

# =====================================================
# 10. 파일 업로드 (메타데이터)
# =====================================================
@router.post("/{project_id}/files")
async def upload_file(project_id: int, file_data: dict, db: AsyncSession = Depends(get_db)):
    """파일 업로드 (메타데이터 저장)"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다.")
        
        new_file = SharedFile(
            team_id=team.team_id,
            file_name=file_data.get("file_name", "unknown"),
            file_size=file_data.get("file_size", 0),
            file_type=file_data.get("file_type", "unknown"),
            file_url=file_data.get("file_url", ""),
            s3_key=file_data.get("s3_key", f"teams/{project_id}/files/{uuid.uuid4()}"),
            uploaded_by=file_data.get("user_id", "unknown"),
            description=file_data.get("description", ""),
        )
        
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        
        return {
            "status": "success",
            "message": "파일이 업로드되었습니다.",
            "data": {
                "file_id": new_file.file_id,
                "file_name": new_file.file_name,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

# =====================================================
# 11. 회의록 목록 조회 (Mock)
# =====================================================
@router.get("/{project_id}/meetings")
async def get_meetings(project_id: int):
    """회의록 목록 조회 (Mock 데이터)"""
    return [
        {
            "id": 1,
            "title": "킥오프 미팅",
            "date": "2025-01-15",
            "content": "프로젝트 시작 미팅",
            "summary": "AI 요약: 프로젝트 시작",
        }
    ]

# =====================================================
# 12. 팀원 초대 링크 생성
# =====================================================
@router.post("/{project_id}/invitations")
async def create_invitation(project_id: int, invitation_data: dict, db: AsyncSession = Depends(get_db)):
    """팀원 초대 링크/코드 생성"""
    try:
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다.")
        
        # 초대 코드 생성
        invitation_code = str(uuid.uuid4())[:8].upper()
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        invitation_link = f"{frontend_url}/#/projects/{project_id}/join?code={invitation_code}"
        
        position_type = convert_position_type(invitation_data.get("position_type", "기타"))
        
        new_invitation = Invitation(
            invitation_id=str(uuid.uuid4()),
            project_id=project_id,
            invitation_code=invitation_code,
            invitation_link=invitation_link,
            invited_by=invitation_data.get("user_id", "unknown"),
            position_type=position_type,
            message=invitation_data.get("message", ""),
            expires_at=datetime.now().replace(day=datetime.now().day + 7),  # 7일 후 만료
        )
        
        db.add(new_invitation)
        await db.commit()
        
        return {
            "status": "success",
            "message": "초대 링크가 생성되었습니다.",
            "data": {
                "invitation_code": invitation_code,
                "invitation_link": invitation_link,
                "expires_at": new_invitation.expires_at.isoformat(),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"초대 링크 생성 실패: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"초대 링크 생성 실패: {str(e)}")
