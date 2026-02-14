from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Any, Dict, List, Optional
import json
from urllib.parse import quote
from app.core.database import get_db
from app.models.enums import TeamRole, StackCategory, MeetingStatus, ReportType
import logging
from datetime import datetime
from app.utils.s3_paths import get_team_s3_key, get_meeting_s3_key, get_file_upload_s3_key
from app.models.team import Team, TeamMember, SharedFile, MeetingSession, GeneratedReport # 모델 추가 import

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# ============= 간단한 팀 API =============

@router.get("/{project_id}/stats")
async def get_team_stats(project_id: int, db: AsyncSession = Depends(get_db)):
    """팀 대시보드 정보 조회 (간단 버전)"""
    try:
        from app.models.team import Team, TeamMember
        
        # 팀 정보 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            # 팀이 없으면 Mock 데이터 반환
            return {
                "team": {
                    "team_id": project_id,
                    "project_id": project_id,
                    "name": f"프로젝트 {project_id} 팀",
                    "created_at": datetime.now().isoformat()
                },
                "members": [
                    {
                        "team_id": project_id,
                        "user_id": "현재사용자",
                        "nickname": "현재사용자",
                        "role": "LEADER",
                        "position_type": "BACKEND",
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "recent_meetings": [],
                "recent_reports": []
            }
        
        # 팀 멤버 조회 (MSA: Auth 서비스에서 사용자 정보 조회)
        members_result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team.team_id)
        )
        members = members_result.scalars().all()
        
        # 실제 팀 데이터
        team_data = {
            "team_id": team.team_id,
            "project_id": team.project_id,
            "name": team.name,
            "created_at": team.created_at.isoformat() if team.created_at else None
        }
        
        # 멤버 데이터 (MSA 클라이언트로 사용자 정보 보강)
        members_data = []
        user_ids = [member.user_id for member in members]
        
        # Auth 서비스에서 사용자 정보 일괄 조회 시도
        users_dict = {}
        try:
            from app.utils.msa_client import MSAClient
            msa_client = MSAClient()
            users_data = await msa_client.get_users_batch(user_ids)
            if users_data:
                users_dict = {u["user_id"]: u for u in users_data}
        except Exception as e:
            logger.warning(f"Auth 서비스 조회 실패: {str(e)}")
        
        for member in members:
            # enum 값에서 클래스명 제거
            role_clean = str(member.role).split('.')[-1] if member.role else 'MEMBER'
            position_clean = str(member.position_type).split('.')[-1] if member.position_type else 'UNKNOWN'
            
            # 사용자 정보가 있으면 nickname 사용, 없으면 user_id
            user_info = users_dict.get(member.user_id, {})
            nickname = user_info.get("nickname", member.user_id)
            
            members_data.append({
                "team_id": member.team_id,
                "user_id": member.user_id,
                "nickname": nickname,
                "role": role_clean,
                "position_type": position_clean,
                "created_at": member.created_at.isoformat() if member.created_at else None,
                "updated_at": member.updated_at.isoformat() if member.updated_at else None
            })
        return {
            "team": team_data,
            "members": members_data,
            "recent_meetings": [],  # Mock 데이터
            "recent_reports": []    # Mock 데이터
        }
        
    except Exception as e:
        logger.error(f"팀 대시보드 조회 실패: {str(e)}")
        # 오류 발생 시 Mock 데이터 반환
        return {
            "team": {
                "team_id": project_id,
                "project_id": project_id,
                "name": f"프로젝트 {project_id} 팀",
                "created_at": datetime.now().isoformat()
            },
            "members": [
                {
                    "team_id": project_id,
                    "user_id": "현재사용자",
                    "nickname": "현재사용자",
                    "role": "LEADER",
                    "position_type": "BACKEND",
                    "updated_at": datetime.now().isoformat()
                }
            ],
            "recent_meetings": [],
            "recent_reports": []
        }

# Mock 데이터 API들
@router.get("/{project_id}/tasks")
async def get_tasks(project_id: int, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """칸반 보드 태스크 조회"""
    try:
        from app.models.task import Task
        
        query = select(Task).where(Task.project_id == project_id)
        
        if status:
            query = query.where(Task.status == status)
            
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return [
            {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, 'value') else task.status,
                "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
                "created_by": task.created_by,
                "assignee_id": task.assignee_id,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat() if task.created_at else None
            } for task in tasks
        ]
    except Exception as e:
        logger.error(f"태스크 조회 실패: {str(e)}")
        # 실패 시 빈 리스트 반환 (프론트엔드 에러 방지)
        return []

@router.get("/{project_id}/files")
async def get_team_files(project_id: int, db: AsyncSession = Depends(get_db)):
    """팀 파일 목록 조회"""
    try:
        from app.models.team import Team
        from app.services.file_service import FileService
        
        # 팀 ID 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            return {"success": True, "files": [], "message": "팀을 찾을 수 없습니다."}
            
        # 파일 목록 조회
        result = await db.execute(
            select(SharedFile)
            .where(SharedFile.team_id == team.team_id)
            .order_by(SharedFile.created_at.desc())
        )
        files = result.scalars().all()
        
        # 파일 서비스로 다운로드 URL 생성
        file_service = FileService()
        
        return {
            "success": True,
            "files": [
                {
                    "file_id": f.file_id,
                    "file_name": f.file_name,
                    "file_size": f.file_size or 0,
                    "file_type": getattr(f, 'file_type', 'unknown') or 'unknown',
                    "uploaded_by": f.uploaded_by or 'unknown',
                    "created_at": f.created_at.isoformat() if f.created_at else "",
                    "s3_key": f.s3_key,
                    "download_url": file_service.get_download_url(f.s3_key) if f.s3_key else None
                }
                for f in files
            ]
        }
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {str(e)}")
        return {"success": False, "files": [], "message": str(e)}

@router.get("/{project_id}/files/{file_id}/download")
async def download_team_file(project_id: int, file_id: int, db: AsyncSession = Depends(get_db)):
    """Stream file download through the backend to avoid S3 CORS."""
    try:
        result = await db.execute(
            select(SharedFile).where(
                SharedFile.project_id == project_id,
                SharedFile.file_id == file_id
            )
        )
        file = result.scalar_one_or_none()
        if not file or not file.s3_key:
            raise HTTPException(status_code=404, detail="File not found")

        from app.services.file_service import FileService
        file_service = FileService()
        body, content_type, content_length = file_service.get_file_stream(file.s3_key)

        filename = file.file_name or "download"
        filename_ascii = "".join(ch if ord(ch) < 128 else "_" for ch in filename) or "download"
        filename_encoded = quote(filename)
        headers = {
            "Content-Disposition": (
                f"attachment; filename=\"{filename_ascii}\"; "
                f"filename*=UTF-8''{filename_encoded}"
            )
        }
        if content_length:
            headers["Content-Length"] = str(content_length)

        return StreamingResponse(body, media_type=content_type, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(status_code=500, detail="File download failed")

@router.get("/{project_id}/meetings")
async def get_meetings(project_id: int):
    """회의록 목록 조회 (Mock 데이터)"""
    return [
        {
            "meeting_id": 1,
            "project_id": project_id,
            "title": "1차 기획 회의",
            "status": "COMPLETED",
            "created_at": datetime.now().isoformat()
        }
    ]


# ============= 누락 API 추가 =============

from pydantic import BaseModel
from typing import Any, Dict, List
import uuid


class TeamUpdateRequest(BaseModel):
    """팀 정보 수정 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class MeetingTriggerRequest(BaseModel):
    """회의 시작/종료 트리거"""
    action: str  # "start" or "stop"
    

class MeetingCreateRequest(BaseModel):
    """회의록 생성 요청"""
    title: str
    content: Optional[str] = None
    date: Optional[str] = None


class MeetingSummaryRequest(BaseModel):
    """회의록 AI 요약 요청"""
    notes: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None


class TaskCreateRequest(BaseModel):
    """태스크 생성 요청"""
    title: str
    description: Optional[str] = None
    status: Optional[str] = "TODO"
    priority: Optional[str] = "MEDIUM"
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    """태스크 수정 요청"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None


class FileUploadRequest(BaseModel):
    """파일 업로드 요청"""
    file_name: str
    file_size: int
    file_type: str
    file_url: str
    s3_key: str
    description: Optional[str] = None


class InvitationCreateRequest(BaseModel):
    """팀원 초대 요청"""
    position_type: str
    message: Optional[str] = None


# 1. 팀 정보 수정 API
@router.patch("/{project_id}")
async def update_team(
    project_id: int,
    request: TeamUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """팀 정보 수정"""
    from app.models.team import Team
    
    try:
        result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="팀을 찾을 수 없습니다."
            )
        
        # 변경할 필드만 업데이트
        if request.name is not None:
            team.name = request.name
        if request.description is not None:
            # description 필드가 없으면 무시
            pass
        if request.status is not None:
            # status 필드가 없으면 무시
            pass
        
        team.updated_at = datetime.now()
        await db.commit()
        await db.refresh(team)
        
        return {
            "success": True,
            "message": "팀 정보가 수정되었습니다.",
            "team": {
                "team_id": team.team_id,
                "project_id": team.project_id,
                "name": team.name,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"팀 정보 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팀 정보 수정 중 오류 발생: {str(e)}"
        )


# 2. 회의 시작/종료 트리거 API
@router.post("/{project_id}/meeting_trigger", status_code=status.HTTP_201_CREATED)
async def trigger_meeting(
    project_id: int,
    request: MeetingTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
    """회의 시작/종료 트리거 (AI 서비스와 연동)"""
    
    if request.action not in ["start", "stop"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action은 'start' 또는 'stop' 이어야 합니다."
        )
    
    # AI 서비스 호출 (MSA 클라이언트 사용)
    try:
        from app.utils.msa_client import MSAClient
        msa_client = MSAClient()
        
        if request.action == "start":
            result = await msa_client.call_ai_meeting_start({
                "team_id": project_id,
                "project_id": project_id
            })
        else:
            result = await msa_client.call_ai_meeting_end({
                "session_id": f"session_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            })
        
        return {
            "success": True,
            "action": request.action,
            "project_id": project_id,
            "message": f"회의가 {'시작' if request.action == 'start' else '종료'}되었습니다.",
            "ai_response": result
        }
    except Exception as e:
        logger.warning(f"AI 서비스 호출 실패, 기본 응답 반환: {str(e)}")
        # AI 서비스 연결 실패 시에도 기본 응답 반환
        return {
            "success": True,
            "action": request.action,
            "project_id": project_id,
            "message": f"회의가 {'시작' if request.action == 'start' else '종료'}되었습니다.",
            "ai_response": None
        }


# 3. 회의 세션 생성 API (ERD: meeting_sessions 테이블 사용)
@router.post("/{project_id}/meetings", status_code=status.HTTP_201_CREATED)
async def create_meeting(
    project_id: int,
    request: MeetingCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """회의 세션 생성"""
    from app.models.team import Team, MeetingSession
    from app.models.enums import MeetingStatus
    
    try:
        # 팀 확인
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="팀을 찾을 수 없습니다."
            )
        
        # 회의 세션 생성 (ERD 기준)
        meeting = MeetingSession(
            team_id=team.team_id,
            project_id=project_id,
            started_at=datetime.now(),
            status=MeetingStatus.IN_PROGRESS
        )
        
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)
        
        return {
            "success": True,
            "message": "회의 세션이 생성되었습니다.",
            "meeting": {
                "session_id": meeting.session_id,
                "team_id": meeting.team_id,
                "project_id": meeting.project_id,
                "title": request.title,
                "content": request.content,
                "status": meeting.status.value if hasattr(meeting.status, 'value') else meeting.status,
                "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                "created_at": meeting.created_at.isoformat() if meeting.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"회의 세션 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회의 세션 생성 중 오류 발생: {str(e)}"
        )


# 4. 회의록 AI 요약 API
@router.post("/{project_id}/meetings/{meeting_id}/summaries", status_code=status.HTTP_200_OK)
async def summarize_meeting(
    project_id: int,
    meeting_id: int,
    request: MeetingSummaryRequest,
    db: AsyncSession = Depends(get_db)
):
    """회의록 AI 요약 요청 (AI 서비스 연동)"""
    
    try:
        from app.utils.msa_client import MSAClient
        msa_client = MSAClient()
        
        # AI 서비스에 요약 요청
        payload_messages = request.messages or [{"content": request.notes or ""}]
        result = await msa_client.call_ai_minutes_generate({
            "team_id": project_id,
            "project_id": project_id,
            "messages": payload_messages
        })

        report = GeneratedReport(
            team_id=project_id,
            project_id=project_id,
            created_by="system",
            report_type=ReportType.MEETING_MINUTES,
            status="COMPLETED",
            title=request.notes or f"Meeting {meeting_id}",
            content=json.dumps(result, ensure_ascii=False)
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        meeting = await db.execute(select(MeetingSession).where(MeetingSession.session_id == meeting_id))
        meeting_session = meeting.scalar_one_or_none()
        if meeting_session:
            meeting_session.generated_report_id = report.report_id
            meeting_session.status = MeetingStatus.COMPLETED
            meeting_session.ended_at = datetime.now()
            await db.commit()

        return {
            "success": True,
            "message": "회의록 AI 요약이 요청되었습니다.",
            "meeting_id": meeting_id,
            "report_id": report.report_id,
            "summary": result
        }
    except Exception as e:
        logger.warning(f"AI 요약 요청 실패: {str(e)}")
        return {
            "success": True,
            "message": "회의록 AI 요약이 요청되었습니다.",
            "meeting_id": meeting_id,
            "summary": {"status": "pending", "notes": request.notes}
        }


# 4-1. 회의록 목록 조회
@router.get("/{project_id}/reports")
async def list_reports(
    project_id: int,
    report_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(GeneratedReport).where(GeneratedReport.team_id == project_id)
        if report_type:
            try:
                report_enum = ReportType(report_type)
                query = query.where(GeneratedReport.report_type == report_enum)
            except Exception:
                pass
        result = await db.execute(query.order_by(GeneratedReport.created_at.desc()))
        reports = result.scalars().all()
        return [
            {
                "report_id": r.report_id,
                "team_id": r.team_id,
                "project_id": r.project_id,
                "report_type": r.report_type.value if hasattr(r.report_type, "value") else r.report_type,
                "status": r.status,
                "title": r.title,
                "s3_key": r.s3_key,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]
    except Exception as e:
        logger.error(f"회의록 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회의록 목록 조회 실패: {str(e)}"
        )


# 4-2. 회의록 내용 조회
@router.get("/{project_id}/reports/{report_id}/content")
async def get_report_content(
    project_id: int,
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(GeneratedReport).where(
                GeneratedReport.team_id == project_id,
                GeneratedReport.report_id == report_id
            )
        )
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다.")

        if report.content:
            try:
                return json.loads(report.content)
            except Exception:
                return {"content": report.content}

        return {"content": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회의록 내용 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회의록 내용 조회 실패: {str(e)}"
        )


# 5. 태스크 생성 API
@router.post("/{project_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: int,
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """태스크 생성"""
    from app.models.task import Task, TaskStatus, TaskPriority
    
    try:
        # 문자열을 Enum으로 변환
        task_status = TaskStatus(request.status) if request.status else TaskStatus.TODO
        task_priority = TaskPriority(request.priority) if request.priority else TaskPriority.MEDIUM
        
        task = Task(
            project_id=project_id,
            title=request.title,
            description=request.description,
            status=task_status,
            priority=task_priority,
            assignee_id=request.assignee_id,
            created_by="current_user",  # 실제로는 인증된 사용자 ID
            due_date=datetime.fromisoformat(request.due_date) if request.due_date else None
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        return {
            "success": True,
            "message": "태스크가 생성되었습니다.",
            "task": {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assignee_id": task.assignee_id,
                "created_by": task.created_by,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"태스크 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"태스크 생성 중 오류 발생: {str(e)}"
        )


# 6. 태스크 수정 API
@router.patch("/{project_id}/tasks/{task_id}")
async def update_task(
    project_id: int,
    task_id: int,
    request: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """태스크 수정 (상태/담당자 변경 등)"""
    from app.models.task import Task, TaskStatus, TaskPriority
    
    try:
        result = await db.execute(
            select(Task).where(Task.task_id == task_id, Task.project_id == project_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="태스크를 찾을 수 없습니다."
            )
        
        # 변경할 필드만 업데이트
        if request.title is not None:
            task.title = request.title
        if request.description is not None:
            task.description = request.description
        if request.status is not None:
            task.status = TaskStatus(request.status)  # Enum으로 변환
        if request.priority is not None:
            task.priority = TaskPriority(request.priority)  # Enum으로 변환
        if request.assignee_id is not None:
            task.assignee_id = request.assignee_id
        if request.due_date is not None:
            task.due_date = datetime.fromisoformat(request.due_date)
        
        task.updated_at = datetime.now()
        await db.commit()
        await db.refresh(task)
        
        return {
            "success": True,
            "message": "태스크가 수정되었습니다.",
            "task": {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assignee_id": task.assignee_id,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"태스크 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"태스크 수정 중 오류 발생: {str(e)}"
        )


# 6-1. 태스크 삭제 API
@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(
    project_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """태스크 삭제"""
    from app.models.task import Task
    
    try:
        result = await db.execute(
            select(Task).where(Task.task_id == task_id, Task.project_id == project_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="태스크를 찾을 수 없습니다."
            )
        
        await db.delete(task)
        await db.commit()
        
        return {
            "success": True,
            "message": "태스크가 삭제되었습니다.",
            "task_id": task_id
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"태스크 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"태스크 삭제 중 오류 발생: {str(e)}"
        )


# 7. 파일 업로드 API (FormData 지원)
@router.post("/{project_id}/files/upload", status_code=status.HTTP_201_CREATED)
async def upload_file_multipart(
    project_id: int,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """파일 업로드 (실제 파일 + 메타데이터 저장)"""
    from app.models.team import Team, SharedFile
    from app.services.file_service import FileService
    
    try:
        # 팀 확인
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="팀을 찾을 수 없습니다."
            )
        
        # S3에 파일 업로드
        file_service = FileService()
        upload_result = file_service.upload_file(file, team.team_id, user_id)
        
        # 다운로드 URL 생성
        download_url = file_service.get_download_url(upload_result["s3_key"])
        
        # 파일 타입 추출
        file_type = file.content_type or "application/octet-stream"
        
        # DB에 메타데이터 저장
        shared_file = SharedFile(
            project_id=project_id,
            team_id=team.team_id,
            file_name=file.filename,
            file_size=upload_result["file_size"],
            file_type=file_type,
            file_url=download_url,
            s3_key=upload_result["s3_key"],
            uploaded_by=user_id,
            description=description
        )
        
        db.add(shared_file)
        await db.commit()
        await db.refresh(shared_file)
        
        return {
            "success": True,
            "message": "파일이 업로드되었습니다.",
            "file": {
                "file_id": shared_file.file_id,
                "name": shared_file.file_name,
                "size": f"{shared_file.file_size / 1024 / 1024:.2f} MB" if shared_file.file_size else "0 MB",
                "type": shared_file.file_type,
                "url": shared_file.file_url,
                "s3_key": shared_file.s3_key,
                "uploaded_by": shared_file.uploaded_by,
                "created_at": shared_file.created_at.isoformat() if shared_file.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"파일 업로드 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류 발생: {str(e)}"
        )


# 7-1. 파일 업로드 API (JSON - 메타데이터만)
@router.post("/{project_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: int,
    request: FileUploadRequest,
    db: AsyncSession = Depends(get_db)
):
    """파일 업로드 (메타데이터 저장)"""
    from app.models.team import SharedFile
    
    try:
        file = SharedFile(
            project_id=project_id,
            file_name=request.file_name,
            file_size=request.file_size,
            file_type=request.file_type,
            file_url=request.file_url,
            s3_key=request.s3_key,
            uploaded_by="current_user",  # 실제로는 인증된 사용자 ID
            description=request.description
        )
        
        db.add(file)
        await db.commit()
        await db.refresh(file)
        
        return {
            "success": True,
            "message": "파일이 업로드되었습니다.",
            "file": {
                "file_id": file.file_id,
                "project_id": file.project_id,
                "file_name": file.file_name,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "file_url": file.file_url,
                "s3_key": file.s3_key,
                "uploaded_by": file.uploaded_by,
                "created_at": file.created_at.isoformat() if file.created_at else None
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"파일 업로드 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류 발생: {str(e)}"
        )


# 8. 팀원 초대 API
@router.post("/{project_id}/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    project_id: int,
    request: InvitationCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """팀원 초대 링크/코드 생성"""
    from app.models.team import Team, Invitation, TeamMember, SharedFile
    from app.models.enums import TeamRole, StackCategory, MeetingStatus, ReportType
    import random
    import string
    
    try:
        # 팀 확인
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="팀을 찾을 수 없습니다."
            )
        
        # 초대 코드 생성
        invitation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        invitation_id = str(uuid.uuid4())
        invitation_link = f"https://portforge.com/invite/{invitation_code}"
        
        # 7일 후 만료
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(days=7)
        
        invitation = Invitation(
            invitation_id=invitation_id,
            project_id=project_id,
            invitation_code=invitation_code,
            invitation_link=invitation_link,
            invited_by="current_user",  # 실제로는 인증된 사용자 ID
            position_type=StackCategory(request.position_type) if request.position_type else StackCategory.BACKEND,
            message=request.message,
            expires_at=expires_at
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        return {
            "success": True,
            "message": "초대 링크가 생성되었습니다.",
            "invitation": {
                "invitation_id": invitation.invitation_id,
                "project_id": invitation.project_id,
                "invitation_code": invitation.invitation_code,
                "invitation_link": invitation.invitation_link,
                "position_type": str(invitation.position_type).split('.')[-1],
                "message": invitation.message,
                "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
                "created_at": invitation.created_at.isoformat() if invitation.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"초대 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"초대 생성 중 오류 발생: {str(e)}"
        )

@router.get("/user/{user_id}/teams")
async def get_user_teams(user_id: str, db: AsyncSession = Depends(get_db)):
    """사용자가 속한 팀 목록 조회"""
    try:
        from app.models.team import Team, TeamMember
        
        # 사용자가 멤버로 속한 팀 조회
        result = await db.execute(
            select(Team, TeamMember)
            .join(TeamMember, Team.team_id == TeamMember.team_id)
            .where(TeamMember.user_id == user_id)
        )
        teams = result.all()
        
        return {
            "status": "success",
            "data": [
                {
                    "team_id": team.team_id,
                    "project_id": team.project_id,
                    "name": team.name,
                    "role": member.role.value if hasattr(member.role, 'value') else member.role,
                    "position": member.position_type.value if hasattr(member.position_type, 'value') else member.position_type,
                    "joined_at": member.created_at.isoformat() if member.created_at else None
                }
                for team, member in teams
            ]
        }
    except Exception as e:
        logger.error(f"사용자 팀 목록 조회 실패: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}

# 중복 API 제거됨 - 파일 목록 조회는 167줄에 정의됨

@router.post("/{project_id}/files")
async def upload_team_file(
    project_id: int,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """팀 파일 업로드 (간단 버전)"""
    try:
        from app.models.team import Team, SharedFile
        import os
        import shutil
        
        # 팀 조회
        team_result = await db.execute(
            select(Team).where(Team.project_id == project_id)
        )
        team = team_result.scalar_one_or_none()
        
        if not team:
            return {"success": False, "message": "팀을 찾을 수 없습니다."}
            
        # 로컬 저장 경로
        upload_dir = f"uploaded_files/{project_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = f"{upload_dir}/{file.filename}"
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)
        
        # DB 저장
        new_file = SharedFile(
            project_id=project_id,
            team_id=team.team_id,
            file_name=file.filename,
            file_size=file_size,
            file_type=file.content_type or "application/octet-stream",
            file_url=f"/api/v1/teams/files/download/{project_id}/{file.filename}",
            s3_key=file_path,
            uploaded_by=user_id,
            description=description
        )
        
        db.add(new_file)
        await db.commit()
        
        return {"success": True, "message": "파일 업로드 완료"}
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}")
        return {"success": False, "message": str(e)}


# ============= 추가 API (프론트엔드 연동용) =============

@router.get("")
async def get_teams(db: AsyncSession = Depends(get_db)):
    """팀 목록 조회"""
    try:
        from app.models.team import Team
        
        result = await db.execute(select(Team).order_by(Team.created_at.desc()))
        teams = result.scalars().all()
        
        return [
            {
                "team_id": team.team_id,
                "project_id": team.project_id,
                "name": team.name,
                "created_at": team.created_at.isoformat() if team.created_at else None
            }
            for team in teams
        ]
    except Exception as e:
        logger.error(f"팀 목록 조회 실패: {str(e)}")
        return []


@router.get("/team/{team_id}")
async def get_team_by_id(team_id: int, db: AsyncSession = Depends(get_db)):
    """팀 상세 조회 (team_id 기준)"""
    try:
        from app.models.team import Team, TeamMember
        
        result = await db.execute(select(Team).where(Team.team_id == team_id))
        team = result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다.")
        
        # 멤버 조회
        members_result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id)
        )
        members = members_result.scalars().all()
        
        return {
            "team_id": team.team_id,
            "project_id": team.project_id,
            "name": team.name,
            "created_at": team.created_at.isoformat() if team.created_at else None,
            "members": [
                {
                    "user_id": m.user_id,
                    "role": str(m.role).split('.')[-1] if m.role else 'MEMBER',
                    "position_type": str(m.position_type).split('.')[-1] if m.position_type else 'UNKNOWN'
                }
                for m in members
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"팀 상세 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_team(team_data: dict, db: AsyncSession = Depends(get_db)):
    """팀 생성"""
    try:
        from app.models.team import Team, TeamMember
        from app.models.enums import TeamRole, StackCategory
        
        project_id = team_data.get("project_id")
        name = team_data.get("name", f"프로젝트 {project_id} 팀")
        leader_id = team_data.get("leader_id")
        leader_position = team_data.get("leader_position", "BACKEND")
        
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id는 필수입니다.")
        
        # 이미 존재하는지 확인
        existing = await db.execute(select(Team).where(Team.project_id == project_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이미 팀이 존재합니다.")
        
        # 팀 생성
        team = Team(
            project_id=project_id,
            name=name
        )
        db.add(team)
        await db.flush()
        
        # 리더 추가
        if leader_id:
            # 포지션 타입 변환
            position_map = {
                "프론트엔드": StackCategory.FRONTEND,
                "백엔드": StackCategory.BACKEND,
                "디자인": StackCategory.DESIGN,
                "FRONTEND": StackCategory.FRONTEND,
                "BACKEND": StackCategory.BACKEND,
                "DESIGN": StackCategory.DESIGN,
                "DB": StackCategory.DB,
                "INFRA": StackCategory.INFRA,
                "기타": StackCategory.ETC,
                "ETC": StackCategory.ETC,
                "스터디원": StackCategory.STUDY_MEMBER,
                "STUDY_MEMBER": StackCategory.STUDY_MEMBER,
            }
            position_type = position_map.get(leader_position, StackCategory.ETC)
            
            leader = TeamMember(
                team_id=team.team_id,
                user_id=leader_id,
                role=TeamRole.LEADER,
                position_type=position_type
            )
            db.add(leader)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "팀이 생성되었습니다.",
            "data": {
                "team_id": team.team_id,
                "project_id": team.project_id,
                "name": team.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"팀 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/members")
async def add_team_member(member_data: dict, db: AsyncSession = Depends(get_db)):
    """팀 멤버 추가 (지원 승인 시 호출됨)"""
    try:
        from app.models.team import Team, TeamMember
        from app.models.enums import TeamRole, StackCategory
        
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
        existing = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.team_id,
                TeamMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "success", "message": "이미 팀 멤버입니다."}
        
        # 포지션 타입 변환
        position_map = {
            "FRONTEND": StackCategory.FRONTEND,
            "BACKEND": StackCategory.BACKEND,
            "DESIGN": StackCategory.DESIGN,
            "DB": StackCategory.DB,
            "INFRA": StackCategory.INFRA,
            "ETC": StackCategory.ETC,
            "스터디원": StackCategory.STUDY_MEMBER,
            "STUDY_MEMBER": StackCategory.STUDY_MEMBER,
        }
        position_type = position_map.get(position_type_str.upper(), StackCategory.ETC)
        
        # 역할 변환
        role = TeamRole.LEADER if role_str.upper() == "LEADER" else TeamRole.MEMBER
        
        # 멤버 추가
        member = TeamMember(
            team_id=team.team_id,
            user_id=user_id,
            role=role,
            position_type=position_type
        )
        db.add(member)
        await db.commit()
        
        logger.info(f"✅ 팀 멤버 추가: {user_id} -> 팀 {team.team_id}")
        
        return {
            "status": "success",
            "message": "팀 멤버가 추가되었습니다.",
            "data": {
                "team_id": team.team_id,
                "user_id": user_id,
                "role": role_str,
                "position_type": position_type_str
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"팀 멤버 추가 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/by-project/{project_id}")
async def delete_team_by_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """프로젝트 ID로 팀 삭제"""
    try:
        from app.models.team import Team, TeamMember
        
        # 팀 조회
        team_result = await db.execute(select(Team).where(Team.project_id == project_id))
        team = team_result.scalar_one_or_none()
        
        if not team:
            return {"status": "success", "message": "삭제할 팀이 없습니다."}
        
        # Delete shared files from S3 first
        from app.services.file_service import FileService
        files_result = await db.execute(select(SharedFile).where(SharedFile.team_id == team.team_id))
        files = files_result.scalars().all()
        file_service = FileService()
        for f in files:
            if f.s3_key:
                try:
                    file_service.delete_file(f.s3_key)
                except Exception as e:
                    logger.warning(f"S3 delete failed: {f.s3_key} ({e})")

        # ? ?? ??
        await db.execute(
            text(f"DELETE FROM team_members WHERE team_id = {team.team_id}")
        )

        # ?? ?? ??? ??
        await db.execute(text(f"DELETE FROM shared_files WHERE team_id = {team.team_id}"))

        # ? ??
        await db.delete(team)
        await db.commit()
        
        return {"status": "success", "message": "팀이 삭제되었습니다."}
    except Exception as e:
        await db.rollback()
        logger.error(f"팀 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
