import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Set
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user
from app.services.chat_service import (
    save_chat_message,
    list_chat_messages,
    upsert_chat_room,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# In-memory websocket connections (per project) for broadcast.
chat_connections: Dict[int, Set[WebSocket]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_message(project_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": payload.get("message_id") or str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": payload.get("user_id") or "unknown",
        "senderName": payload.get("senderName") or payload.get("user_name") or "Unknown",
        "message": payload.get("message") or payload.get("text") or "",
        "timestamp": payload.get("timestamp") or _now_iso(),
        "created_at": payload.get("created_at") or _now_iso(),
    }


@router.get("/chat/{project_id}/messages", response_model=ResponseEnvelope)
async def get_messages(project_id: int, current_user=Depends(get_current_user)):
    data = await list_chat_messages(project_id, limit=100)
    return ResponseEnvelope(success=True, code="CHAT_000", message="Messages", data=data)


@router.post("/chat/{project_id}/messages", response_model=ResponseEnvelope)
async def post_message(project_id: int, body: Dict[str, Any], current_user=Depends(get_current_user)):
    msg = _build_message(project_id, body)
    # Persist to DynamoDB (ensures required fields)
    try:
        saved = await save_chat_message(project_id, msg)
        # also keep senderName for FE display
        saved["senderName"] = msg["senderName"]
    except Exception as e:
        logger.exception("Failed to save chat message")
        return ResponseEnvelope(success=False, code="CHAT_500", message="Failed to save message", data=None)

    # Update chat room recency for the user
    try:
        await upsert_chat_room(str(msg["user_id"]), project_id)
    except Exception:
        logger.exception("Failed to upsert chat room")

    # Broadcast to live connections, if any.
    for ws in list(chat_connections.get(project_id, set())):
        try:
            await ws.send_json(saved)
        except Exception:
            chat_connections[project_id].discard(ws)
    return ResponseEnvelope(success=True, code="CHAT_001", message="Message sent", data=saved)


@router.websocket("/ws/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: int):
    await websocket.accept()
    connections = chat_connections.setdefault(project_id, set())
    connections.add(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON payload"})
                continue

            msg = _build_message(project_id, payload)
            try:
                saved = await save_chat_message(project_id, msg)
                saved["senderName"] = msg["senderName"]
            except Exception:
                logger.exception("Failed to save chat message via WS")
                await websocket.send_json({"error": "Failed to save message"})
                continue

            try:
                await upsert_chat_room(str(msg["user_id"]), project_id)
            except Exception:
                logger.exception("Failed to upsert chat room")

            # Broadcast to all connections in the same project.
            for ws in list(connections):
                try:
                    await ws.send_json(saved)
                except Exception:
                    connections.discard(ws)
    except WebSocketDisconnect:
        connections.discard(websocket)
    finally:
        connections.discard(websocket)


# ==============================================================================
# FE_latest 호환용 라우터 (TeamSpacePage.tsx 대응)
# ==============================================================================
from typing import Optional
from pydantic import BaseModel

class ChatMessageCompatRequest(BaseModel):
    team_id: int
    project_id: int
    user: str   # FE에서는 닉네임을 user필드에 담아 보냄
    message: str
    is_in_meeting: bool = False

@router.post("/chat/message")
async def save_chat_message_compat(req: ChatMessageCompatRequest):
    """
    FE_latest(TeamSpacePage) 호환용 메시지 저장 API
    Endpoint: POST /chat/message
    """
    # FE에서는 team_id/project_id를 제공합니다. 
    # 채팅방 식별자로 project_id를 사용하겠습니다. (기존 로직 따름)
    
    payload = {
        "user_id": req.user,  # user_id 필드에 닉네임 저장 (auth user_id가 아님 주의)
        "message": req.message,
        "senderName": req.user,
    }
    
    # DynamoDB 테이블이 없어도 FE가 동작하도록 예외 처리
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%H:%M")
    ts = int(now.timestamp() * 1000)
    
    try:
        saved = await save_chat_message(req.project_id, payload)
        # timestamp 파싱
        if saved.get("timestamp"):
            try:
                t_str = saved["timestamp"].replace("Z", "+00:00")
                dt = datetime.fromisoformat(t_str)
                time_str = dt.strftime("%H:%M")
                ts = int(dt.timestamp() * 1000)
            except Exception:
                pass
        return {
            "user": saved["user_id"],
            "msg": saved["message"],
            "time": time_str,
            "timestamp": ts,
            "is_in_meeting": req.is_in_meeting
        }
    except Exception as e:
        logger.warning(f"채팅 메시지 저장 실패 (테이블 미존재 가능): {e}")
        # 저장 실패해도 FE에게는 성공처럼 응답 (로컬에서만 보임)
        return {
            "user": req.user,
            "msg": req.message,
            "time": time_str,
            "timestamp": ts,
            "is_in_meeting": req.is_in_meeting
        }

@router.get("/chat/messages/{team_id}/{project_id}")
async def get_messages_compat(
    team_id: int,
    project_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
):
    """
    FE_latest 호환용 메시지 목록 조회
    Endpoint: GET /chat/messages/{team_id}/{project_id}
    """
    # project_id로 조회 (DynamoDB 테이블이 없으면 빈 배열 반환)
    try:
        use_limit = None if (start_date or end_date) else (limit if limit is not None else 100)
        data = await list_chat_messages(
            project_id,
            limit=use_limit,
            start_time=start_date,
            end_time=end_date,
        )
    except Exception as e:
        logger.warning(f"채팅 메시지 조회 실패 (테이블 미존재 가능): {e}")
        return {"messages": [], "count": 0}
    
    # FE 형식으로 변환
    messages = []
    for d in data:
        ts = 0
        time_str = ""
        if d.get("timestamp"):
            try:
                t_str = d["timestamp"].replace("Z", "+00:00")
                dt = datetime.fromisoformat(t_str)
                ts = int(dt.timestamp() * 1000)
                time_str = dt.strftime("%H:%M")
            except:
                pass
                
        messages.append({
            "user": d.get("user_id"),
            "msg": d.get("message"),
            "time": time_str,
            "timestamp": ts,
            "isInMeeting": False 
        })
        
    return {
        "messages": messages,
        "count": len(messages)
    }

