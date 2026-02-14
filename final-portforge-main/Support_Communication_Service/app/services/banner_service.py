from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Banner


async def list_banners() -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        stmt = select(Banner).order_by(Banner.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "banner_id": b.banner_id,
                "title": b.title,
                "link": b.link,
                "is_active": b.is_active,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
            }
            for b in rows
        ]


async def create_banner(title: str, link: Optional[str], is_active: bool = True) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        banner = Banner(title=title, link=link, is_active=is_active)
        session.add(banner)
        await session.commit()
        await session.refresh(banner)
        return {
            "banner_id": banner.banner_id,
            "title": banner.title,
            "link": banner.link,
            "is_active": banner.is_active,
            "created_at": banner.created_at,
            "updated_at": banner.updated_at,
        }


async def update_banner(banner_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        banner = await session.get(Banner, banner_id)
        if not banner:
            return None
        if "title" in payload:
            banner.title = payload["title"]
        if "link" in payload:
            banner.link = payload["link"]
        if "is_active" in payload:
            banner.is_active = bool(payload["is_active"])
        await session.commit()
        await session.refresh(banner)
        return {
            "banner_id": banner.banner_id,
            "title": banner.title,
            "link": banner.link,
            "is_active": banner.is_active,
            "created_at": banner.created_at,
            "updated_at": banner.updated_at,
        }


async def delete_banner(banner_id: int) -> bool:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        banner = await session.get(Banner, banner_id)
        if not banner:
            return False
        await session.delete(banner)
        await session.commit()
        return True
