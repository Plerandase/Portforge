from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.base import ResponseEnvelope
from app.core.deps import get_current_user

router = APIRouter()


class EventCreateRequest(BaseModel):
    title: str
    category: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class EventUpdateRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.get("", response_model=ResponseEnvelope)
async def list_events(category: str | None = None):
    events = [
        {"id": 1, "title": "Hackathon", "category": "해커톤"},
        {"id": 2, "title": "Conference", "category": "컨퍼런스"},
    ]
    if category:
        events = [e for e in events if e["category"] == category]
    return ResponseEnvelope(success=True, code="EVT_000", message="Events", data=events)


@router.post("", response_model=ResponseEnvelope, status_code=201)
async def create_event(payload: EventCreateRequest, current_user=Depends(get_current_user)):
    event = {"id": 3, **payload.model_dump()}
    return ResponseEnvelope(success=True, code="EVT_001", message="Event created", data=event)


@router.get("/{event_id}", response_model=ResponseEnvelope)
async def get_event(event_id: int):
    event = {"id": event_id, "title": "Hackathon", "category": "해커톤", "description": "Sample event"}
    return ResponseEnvelope(success=True, code="EVT_002", message="Event detail", data=event)


@router.patch("/{event_id}", response_model=ResponseEnvelope)
async def update_event(event_id: int, payload: EventUpdateRequest, current_user=Depends(get_current_user)):
    updated = {"id": event_id, **payload.model_dump(exclude_none=True)}
    return ResponseEnvelope(success=True, code="EVT_003", message="Event updated", data=updated)


@router.delete("/{event_id}", response_model=ResponseEnvelope)
async def delete_event(event_id: int, current_user=Depends(get_current_user)):
    return ResponseEnvelope(success=True, code="EVT_004", message="Event deleted", data={"id": event_id})
