# Repository model

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
from typing import List, Optional

from app.core.database import Base


class Repository(Base):
    __tablename__ = "repositories"
    
    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    url = Column(String(512), nullable=False)
    description = Column(Text)
    
    # GitHub metadata
    star_count = Column(Integer, default=0)
    fork_count = Column(Integer, default=0)
    language = Column(String(100))
    license = Column(String(100))
    
    # Repository status
    is_active = Column(Boolean, default=True)
    submodule_path = Column(String(512))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_synced_at = Column(DateTime(timezone=True))
    
    # Relationships
    agents = relationship("Agent", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository(name='{self.name}', star_count={self.star_count})>"
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> "Repository":
        """Create a new repository"""
        repository = cls(**kwargs)
        session.add(repository)
        await session.flush()
        return repository
    
    @classmethod
    async def get_by_name(cls, session: AsyncSession, name: str) -> Optional["Repository"]:
        """Get repository by name"""
        stmt = select(cls).where(cls.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_all_active(cls, session: AsyncSession) -> List["Repository"]:
        """Get all active repositories"""
        stmt = select(cls).where(cls.is_active == True).order_by(cls.star_count.desc())
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        """Count total repositories"""
        stmt = select(func.count(cls.id))
        result = await session.execute(stmt)
        return result.scalar()
    
    async def update_github_metadata(self, session: AsyncSession, metadata: dict):
        """Update GitHub metadata"""
        self.star_count = metadata.get("stargazers_count", 0)
        self.fork_count = metadata.get("forks_count", 0)
        self.language = metadata.get("language")
        self.license = metadata.get("license", {}).get("name") if metadata.get("license") else None
        self.updated_at = datetime.utcnow()
        await session.flush()
    
    async def mark_synced(self, session: AsyncSession):
        """Mark repository as synced"""
        self.last_synced_at = datetime.utcnow()
        await session.flush()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "star_count": self.star_count,
            "fork_count": self.fork_count,
            "language": self.language,
            "license": self.license,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None
        }