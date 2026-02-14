from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.schemas.chat import ChatMessageRequest
import uuid
from app.services.chat_service import save_chat_message, list_chat_messages, upsert_chat_room

router = APIRouter()


class TeamCreateRequest(BaseModel):
    title: str
    description: str | None = None
    stacks: list[str] | None = None
    end_date: str | None = None


class TeamUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    members: list[str] | None = None


# Local ChatMessageRequest removed in favor of app.schemas.chat


class MeetingRequest(BaseModel):
    title: str
    content: str | None = None
    date: str | None = None


class MeetingSummaryRequest(BaseModel):
    notes: str | None = None


class TaskRequest(BaseModel):
    title: str
    status: str | None = "todo"
    assignee: str | None = None


class TaskUpdateRequest(BaseModel):
    status: str | None = None
    assignee: str | None = None


class FileUploadRequest(BaseModel):
    filename: str
    url: str | None = None


class MeetingTriggerRequest(BaseModel):
    action: str  # start | stop


@router.post("", response_model=ResponseEnvelope, status_code=201)
async def create_team(payload: TeamCreateRequest, current_user=Depends(get_current_user)):
    team = {
        "id": 1,
        "title": payload.title,
        "description": payload.description,
        "owner_id": current_user["id"],
        "status": "모집중",
    }
    return ResponseEnvelope(success=True, code="TEAM_000", message="Team created", data=team)


@router.patch("/{project_id}", response_model=ResponseEnvelope)
async def update_team(project_id: int, payload: TeamUpdateRequest, current_user=Depends(get_current_user)):
    updated = {"id": project_id, **payload.model_dump(exclude_none=True)}
    return ResponseEnvelope(success=True, code="TEAM_001", message="Team updated", data=updated)


@router.get("/{project_id}/chats", response_model=ResponseEnvelope)
async def list_chats(
    project_id: int, 
    current_user=Depends(get_current_user),
):
    chats = await list_chat_messages(project_id, limit=100)
    return ResponseEnvelope(success=True, code="TEAM_002", message="Chat history", data=chats)


@router.post("/{project_id}/chats", response_model=ResponseEnvelope)
async def post_chat(
    project_id: int, 
    payload: ChatMessageRequest, 
    current_user=Depends(get_current_user),
):
    user_id_val = current_user.get("id")
    sender_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id_val)))

    message_payload = {
        "user_id": sender_uuid,
        "message": payload.message,
        "message_type": payload.message_type,
        "senderName": current_user.get("name", "Unknown"),
    }
    saved = await save_chat_message(project_id, message_payload)
    await upsert_chat_room(sender_uuid, project_id)
    return ResponseEnvelope(success=True, code="TEAM_003", message="Message sent", data=saved)


@router.post("/{project_id}/meeting_trigger", response_model=ResponseEnvelope, status_code=201)
async def trigger_meeting(project_id: int, payload: MeetingTriggerRequest, current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="TEAM_004", message=f"Meeting {payload.action}", data={"project_id": project_id, "action": payload.action})


@router.get("/{project_id}/meetings", response_model=ResponseEnvelope)
async def list_meetings(project_id: int, current_user=Depends(get_current_user)):
    meetings = [
        {"id": 1, "title": "Kickoff", "content": "Introduce team", "date": "2024-01-02"},
    ]
    return ResponseEnvelope(success=True, code="TEAM_005", message="Meetings", data=meetings)


@router.post("/{project_id}/meetings", response_model=ResponseEnvelope, status_code=201)
async def create_meeting(project_id: int, payload: MeetingRequest, current_user=Depends(get_current_user)):
    meeting = {"id": 2, "project_id": project_id, **payload.model_dump()}
    return ResponseEnvelope(success=True, code="TEAM_006", message="Meeting created", data=meeting)


@router.post("/{project_id}/meetings/{meeting_id}/summaries", response_model=ResponseEnvelope)
async def summarize_meeting(project_id: int, meeting_id: int, payload: MeetingSummaryRequest, current_user=Depends(get_current_user)):
    summary = payload.notes or "Summary generated."
    return ResponseEnvelope(success=True, code="TEAM_007", message="Meeting summarized", data={"meeting_id": meeting_id, "summary": summary})


@router.get("/{project_id}/tasks", response_model=ResponseEnvelope)
async def list_tasks(project_id: int, current_user=Depends(get_current_user)):
    tasks = [
        {"id": 1, "title": "Design UI", "status": "doing", "assignee": "designer"},
        {"id": 2, "title": "Set up backend", "status": "todo", "assignee": "backend"},
    ]
    return ResponseEnvelope(success=True, code="TEAM_008", message="Tasks", data=tasks)


@router.post("/{project_id}/tasks", response_model=ResponseEnvelope, status_code=201)
async def create_task(project_id: int, payload: TaskRequest, current_user=Depends(get_current_user)):
    task = {"id": 3, "project_id": project_id, **payload.model_dump()}
    return ResponseEnvelope(success=True, code="TEAM_009", message="Task created", data=task)


@router.patch("/{project_id}/tasks/{task_id}", response_model=ResponseEnvelope)
async def update_task(project_id: int, task_id: int, payload: TaskUpdateRequest, current_user=Depends(get_current_user)):
    updated = {"id": task_id, "project_id": project_id, **payload.model_dump(exclude_none=True)}
    return ResponseEnvelope(success=True, code="TEAM_010", message="Task updated", data=updated)


@router.get("/{project_id}/files", response_model=ResponseEnvelope)
async def list_files(project_id: int, current_user=Depends(get_current_user)):
    files = [{"id": 1, "filename": "spec.pdf", "url": "https://files.example.com/spec.pdf"}]
    return ResponseEnvelope(success=True, code="TEAM_011", message="Files", data=files)


@router.post("/{project_id}/files", response_model=ResponseEnvelope, status_code=201)
async def upload_file(project_id: int, payload: FileUploadRequest, current_user=Depends(get_current_user)):
    file_info = {
        "id": 2,
        "filename": payload.filename,
        "url": payload.url or f"https://files.example.com/{payload.filename}",
    }
    return ResponseEnvelope(success=True, code="TEAM_012", message="File uploaded", data=file_info)


@router.get("/{project_id}/members", response_model=ResponseEnvelope)
async def list_members(project_id: int, current_user=Depends(get_current_user)):
    members = [
        {"id": 1, "name": "Leader", "role": "Leader"},
        {"id": 2, "name": "Member", "role": "Member"},
    ]
    return ResponseEnvelope(success=True, code="TEAM_013", message="Members", data=members)


@router.post("/{project_id}/invitations", response_model=ResponseEnvelope, status_code=201)
async def create_invitation(project_id: int, current_user=Depends(get_current_user)):
    invitation = {
        "project_id": project_id,
        "link": f"https://app.example.com/invite/{project_id}/abc123",
        "code": "ABC123",
    }
    return ResponseEnvelope(success=True, code="TEAM_014", message="Invitation created", data=invitation)


@router.get("/{project_id}/stats", response_model=ResponseEnvelope)
async def get_stats(project_id: int, current_user=Depends(get_current_user)):
    stats = {
        "progress": 42,
        "tasks_open": 5,
        "tasks_done": 12,
        "d_day": "D-10",
    }
    return ResponseEnvelope(success=True, code="TEAM_015", message="Stats", data=stats)
