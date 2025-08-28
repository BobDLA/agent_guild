# TechStack model

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional, Dict

from app.core.database import Base


class TechStack(Base):
    __tablename__ = "tech_stacks"
    
    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    agent = relationship("Agent", back_populates="tech_stacks")
    
    # Technology information
    tag = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<TechStack(agent_id={self.agent_id}, tag='{self.tag}', category='{self.category}')>"
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> "TechStack":
        """Create a new tech stack entry"""
        tech_stack = cls(**kwargs)
        session.add(tech_stack)
        await session.flush()
        return tech_stack
    
    @classmethod
    async def create_multiple(cls, session: AsyncSession, agent_id: int, tags: List[Dict[str, str]]):
        """Create multiple tech stack entries for an agent"""
        tech_stacks = []
        for tag_data in tags:
            tech_stack = cls(
                agent_id=agent_id,
                tag=tag_data["tag"],
                category=tag_data.get("category", "general")
            )
            session.add(tech_stack)
            tech_stacks.append(tech_stack)
        
        await session.flush()
        return tech_stacks
    
    @classmethod
    async def get_by_agent_id(cls, session: AsyncSession, agent_id: int) -> List["TechStack"]:
        """Get all tech stack entries for an agent"""
        stmt = select(cls).where(cls.agent_id == agent_id).order_by(cls.category, cls.tag)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_popular_tags(cls, session: AsyncSession, category: Optional[str] = None, limit: int = 20) -> List[Dict[str, any]]:
        """Get most popular technology tags"""
        stmt = select(
            cls.tag,
            cls.category,
            func.count(cls.id).label("usage_count")
        ).group_by(cls.tag, cls.category).order_by(func.count(cls.id).desc())
        
        if category:
            stmt = stmt.where(cls.category == category)
        
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        
        return [
            {
                "tag": row.tag,
                "category": row.category,
                "usage_count": row.usage_count
            }
            for row in result.all()
        ]
    
    @classmethod
    async def get_categories(cls, session: AsyncSession) -> List[str]:
        """Get all unique categories"""
        stmt = select(cls.category).distinct().order_by(cls.category)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
    
    @classmethod
    async def get_tags_by_category(cls, session: AsyncSession, category: str) -> List[str]:
        """Get all tags in a specific category"""
        stmt = select(cls.tag).where(cls.category == category).distinct().order_by(cls.tag)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
    
    @classmethod
    async def delete_for_agent(cls, session: AsyncSession, agent_id: int):
        """Delete all tech stack entries for an agent"""
        stmt = delete(cls).where(cls.agent_id == agent_id)
        await session.execute(stmt)
        await session.flush()
    
    @classmethod
    async def get_related_agents(cls, session: AsyncSession, tags: List[str], exclude_agent_id: Optional[int] = None, limit: int = 10) -> List[int]:
        """Get agent IDs that share similar tech stacks"""
        stmt = select(cls.agent_id, func.count(cls.id).label("match_count")).where(
            cls.tag.in_(tags)
        ).group_by(cls.agent_id).order_by(func.count(cls.id).desc())
        
        if exclude_agent_id:
            stmt = stmt.where(cls.agent_id != exclude_agent_id)
        
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        
        return [row.agent_id for row in result.all()]
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tag": self.tag,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }