from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Event, EventCategory


def _normalize_event_date(value: Any) -> Any:
    """
    Accept empty string as None to avoid MySQL DATETIME errors.
    """
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


async def list_events(category: Optional[str] = None) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(Event).order_by(Event.created_at.desc())
        if category:
            try:
                cat_enum = EventCategory(category)
                stmt = stmt.where(Event.category == cat_enum)
            except ValueError:
                # If invalid category, return empty list
                return []
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "event_id": e.event_id,
                "title": e.title,
                "category": e.category.value if e.category else None,
                "event_description": e.event_description,
                "image_url": e.image_url,
                "event_date": e.event_date,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
            }
            for e in rows
        ]


async def create_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        event_date = _normalize_event_date(payload.get("event_date"))
        event = Event(
            title=payload.get("title"),
            category=EventCategory(payload["category"]) if payload.get("category") else None,
            event_description=payload.get("event_description"),
            image_url=payload.get("image_url"),
            event_date=event_date,
            updated_at=datetime.utcnow(),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return {
            "event_id": event.event_id,
            "title": event.title,
            "category": event.category.value if event.category else None,
            "event_description": event.event_description,
            "image_url": event.image_url,
            "event_date": event.event_date,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }


async def get_event(event_id: int) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        event = await session.get(Event, event_id)
        if not event:
            return None
        return {
            "event_id": event.event_id,
            "title": event.title,
            "category": event.category.value if event.category else None,
            "event_description": event.event_description,
            "image_url": event.image_url,
            "event_date": event.event_date,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }


async def update_event(event_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        event = await session.get(Event, event_id)
        if not event:
            return None
        if "title" in payload:
            event.title = payload["title"]
        if "category" in payload:
            event.category = EventCategory(payload["category"]) if payload["category"] else None
        if "event_description" in payload:
            event.event_description = payload["event_description"]
        if "image_url" in payload:
            event.image_url = payload["image_url"]
        if "event_date" in payload:
            event.event_date = _normalize_event_date(payload["event_date"])
        event.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(event)
        return {
            "event_id": event.event_id,
            "title": event.title,
            "category": event.category.value if event.category else None,
            "event_description": event.event_description,
            "image_url": event.image_url,
            "event_date": event.event_date,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }


async def delete_event(event_id: int) -> bool:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        event = await session.get(Event, event_id)
        if not event:
            return False
        await session.delete(event)
        await session.commit()
        return True
