# Classification model

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
from typing import List, Optional, Dict

from app.core.database import Base


class Classification(Base):
    __tablename__ = "classifications"
    
    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    agent = relationship("Agent", back_populates="classifications")
    
    # Classification categories
    lifecycle_phase = Column(String(100), nullable=False, index=True)
    role_type = Column(String(100), nullable=False, index=True)
    
    # Classification metadata
    confidence_score = Column(Float, nullable=False)
    is_ai_generated = Column(Boolean, default=True)
    
    # Manual review fields
    is_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String(100))
    review_notes = Column(String(512))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    classified_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Classification(agent_id={self.agent_id}, lifecycle='{self.lifecycle_phase}', role='{self.role_type}', confidence={self.confidence_score})>"
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> "Classification":
        """Create a new classification"""
        if "classified_at" not in kwargs:
            kwargs["classified_at"] = datetime.utcnow()
        
        classification = cls(**kwargs)
        session.add(classification)
        await session.flush()
        return classification
    
    @classmethod
    async def get_by_agent_id(cls, session: AsyncSession, agent_id: int) -> List["Classification"]:
        """Get all classifications for an agent"""
        stmt = select(cls).where(cls.agent_id == agent_id).order_by(cls.confidence_score.desc())
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_primary_for_agent(cls, session: AsyncSession, agent_id: int) -> Optional["Classification"]:
        """Get primary (highest confidence) classification for an agent"""
        stmt = select(cls).where(cls.agent_id == agent_id).order_by(cls.confidence_score.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_distribution_stats(cls, session: AsyncSession) -> Dict[str, Dict[str, int]]:
        """Get classification distribution statistics"""
        # Lifecycle phase distribution
        lifecycle_stmt = select(
            cls.lifecycle_phase,
            func.count(cls.id).label("count")
        ).group_by(cls.lifecycle_phase)
        lifecycle_result = await session.execute(lifecycle_stmt)
        lifecycle_dist = dict(lifecycle_result.all())
        
        # Role type distribution
        role_stmt = select(
            cls.role_type,
            func.count(cls.id).label("count")
        ).group_by(cls.role_type)
        role_result = await session.execute(role_stmt)
        role_dist = dict(role_result.all())
        
        return {
            "lifecycle_phases": lifecycle_dist,
            "role_types": role_dist
        }
    
    @classmethod
    async def get_low_confidence(cls, session: AsyncSession, threshold: float = 0.6) -> List["Classification"]:
        """Get classifications with low confidence for manual review"""
        stmt = select(cls).where(
            cls.confidence_score < threshold,
            cls.is_reviewed == False
        ).order_by(cls.confidence_score.asc())
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def mark_reviewed(
        self, 
        session: AsyncSession, 
        reviewed_by: str, 
        notes: Optional[str] = None,
        new_lifecycle: Optional[str] = None,
        new_role: Optional[str] = None
    ):
        """Mark classification as manually reviewed"""
        self.is_reviewed = True
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.review_notes = notes
        
        # Update classification if changed
        if new_lifecycle:
            self.lifecycle_phase = new_lifecycle
        if new_role:
            self.role_type = new_role
        
        await session.flush()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "lifecycle_phase": self.lifecycle_phase,
            "role_type": self.role_type,
            "confidence_score": self.confidence_score,
            "is_ai_generated": self.is_ai_generated,
            "is_reviewed": self.is_reviewed,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "classified_at": self.classified_at.isoformat() if self.classified_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None
        }