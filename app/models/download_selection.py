# DownloadSelection model

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from app.core.database import Base


class DownloadSelection(Base):
    __tablename__ = "download_selections"
    
    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    agent = relationship("Agent", back_populates="download_selections")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    selected_at = Column(DateTime(timezone=True), nullable=False)
    
    def __repr__(self):
        return f"<DownloadSelection(session_id='{self.session_id}', agent_id={self.agent_id})>"
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> "DownloadSelection":
        """Create a new download selection"""
        if "selected_at" not in kwargs:
            kwargs["selected_at"] = datetime.utcnow()
        
        selection = cls(**kwargs)
        session.add(selection)
        await session.flush()
        return selection
    
    @classmethod
    async def add_to_selection(cls, session: AsyncSession, session_id: str, agent_id: int) -> "DownloadSelection":
        """Add an agent to download selection"""
        # Check if already selected
        existing = await cls.get_selection_item(session, session_id, agent_id)
        if existing:
            return existing
        
        return await cls.create(
            session,
            session_id=session_id,
            agent_id=agent_id
        )
    
    @classmethod
    async def remove_from_selection(cls, session: AsyncSession, session_id: str, agent_id: int):
        """Remove an agent from download selection"""
        stmt = delete(cls).where(
            and_(cls.session_id == session_id, cls.agent_id == agent_id)
        )
        await session.execute(stmt)
        await session.flush()
    
    @classmethod
    async def get_selection_item(cls, session: AsyncSession, session_id: str, agent_id: int) -> Optional["DownloadSelection"]:
        """Get specific selection item"""
        stmt = select(cls).where(
            and_(cls.session_id == session_id, cls.agent_id == agent_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_session_selections(cls, session: AsyncSession, session_id: str) -> List["DownloadSelection"]:
        """Get all selections for a session"""
        stmt = select(cls).where(cls.session_id == session_id).order_by(cls.selected_at)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_session_agent_ids(cls, session: AsyncSession, session_id: str) -> List[int]:
        """Get agent IDs for a session"""
        stmt = select(cls.agent_id).where(cls.session_id == session_id)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
    
    @classmethod
    async def clear_session_selections(cls, session: AsyncSession, session_id: str):
        """Clear all selections for a session"""
        stmt = delete(cls).where(cls.session_id == session_id)
        await session.execute(stmt)
        await session.flush()
    
    @classmethod
    async def get_download_stats(cls, session: AsyncSession, days: int = 30) -> List[Dict[str, any]]:
        """Get download statistics for agents"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(
            cls.agent_id,
            func.count(cls.id).label("download_count"),
            func.count(func.distinct(cls.session_id)).label("unique_sessions")
        ).where(
            cls.selected_at >= cutoff_date
        ).group_by(cls.agent_id).order_by(func.count(cls.id).desc())
        
        result = await session.execute(stmt)
        
        return [
            {
                "agent_id": row.agent_id,
                "download_count": row.download_count,
                "unique_sessions": row.unique_sessions
            }
            for row in result.all()
        ]
    
    @classmethod
    async def get_popular_agents(cls, session: AsyncSession, limit: int = 10, days: int = 30) -> List[int]:
        """Get most popular agent IDs by download count"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(
            cls.agent_id,
            func.count(cls.id).label("download_count")
        ).where(
            cls.selected_at >= cutoff_date
        ).group_by(cls.agent_id).order_by(func.count(cls.id).desc()).limit(limit)
        
        result = await session.execute(stmt)
        return [row.agent_id for row in result.all()]
    
    @classmethod
    async def cleanup_old_selections(cls, session: AsyncSession, days: int = 7):
        """Clean up old download selections"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(cls).where(cls.created_at < cutoff_date)
        result = await session.execute(stmt)
        await session.flush()
        
        return result.rowcount
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "selected_at": self.selected_at.isoformat() if self.selected_at else None
        }