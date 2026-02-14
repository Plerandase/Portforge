from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import Notification


async def create_notification(
    user_id: str,
    message: str,
    link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insert a notification row and return it as dict.
    """
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        notif = Notification(
            user_id=user_id,
            message=message,
            link=link,
        )
        session.add(notif)
        await session.commit()
        await session.refresh(notif)
        return {
            "notification_id": notif.notification_id,
            "user_id": notif.user_id,
            "message": notif.message,
            "link": notif.link,
            "is_read": notif.is_read,
            "created_at": notif.created_at,
        }


async def list_notifications(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch notifications, optionally filtered by user_id.
    """
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(Notification)
        if user_id:
            stmt = stmt.where(Notification.user_id == user_id)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "notification_id": n.notification_id,
                "user_id": n.user_id,
                "message": n.message,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in rows
        ]


async def mark_notifications_read(user_id: str) -> int:
    """
    Mark all notifications for a user as read.
    Returns the number of updated rows.
    """
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        
        count = 0
        for n in rows:
            n.is_read = True
            count += 1
        
        await session.commit()
        return count

