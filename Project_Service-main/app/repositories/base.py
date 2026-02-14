from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get entity by ID"""
        result = self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination"""
        result = self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    def create(self, **kwargs) -> ModelType:
        """Create new entity"""
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update entity by ID"""
        self.db.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        self.db.commit()
        return self.get_by_id(id)
    
    def delete(self, id: int) -> bool:
        """Delete entity by ID"""
        result = self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        self.db.commit()
        return result.rowcount > 0