from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Notice


async def create_notice(title: str, content: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        notice = Notice(title=title, content=content)
        session.add(notice)
        await session.commit()
        await session.refresh(notice)
        return {
            "notice_id": notice.notice_id,
            "title": notice.title,
            "content": notice.content,
            "created_at": notice.created_at,
        }


async def list_notices(limit: int = 50) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(Notice).order_by(Notice.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "notice_id": n.notice_id,
                "title": n.title,
                "content": n.content,
                "created_at": n.created_at,
            }
            for n in rows
        ]


async def update_notice(notice_id: int, title: str, content: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        notice = await session.get(Notice, notice_id)
        if not notice:
            raise ValueError("Notice not found")
        notice.title = title
        notice.content = content
        await session.commit()
        await session.refresh(notice)
        return {
            "notice_id": notice.notice_id,
            "title": notice.title,
            "content": notice.content,
            "created_at": notice.created_at,
        }


async def delete_notice(notice_id: int) -> None:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        notice = await session.get(Notice, notice_id)
        if not notice:
            return
        await session.delete(notice)
        await session.commit()
