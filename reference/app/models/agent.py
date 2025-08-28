# Agent model

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"
    
    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    file_path = Column(String(512), nullable=False)
    
    # Repository relationship
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    repository = relationship("Repository", back_populates="agents")
    
    # Agent content
    system_prompt = Column(Text)
    yaml_metadata = Column(JSON)
    content_hash = Column(String(64))  # For detecting changes
    
    # Processing status
    is_parsed = Column(Boolean, default=False)
    is_classified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    parsed_at = Column(DateTime(timezone=True))
    
    # Relationships
    classifications = relationship("Classification", back_populates="agent", cascade="all, delete-orphan")
    tech_stacks = relationship("TechStack", back_populates="agent", cascade="all, delete-orphan")
    download_selections = relationship("DownloadSelection", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(name='{self.name}', repository='{self.repository.name if self.repository else 'Unknown'}')>"
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> "Agent":
        """Create a new agent"""
        agent = cls(**kwargs)
        session.add(agent)
        await session.flush()
        return agent
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, agent_id: int) -> Optional["Agent"]:
        """Get agent by ID with relationships"""
        stmt = select(cls).where(cls.id == agent_id).options(
            selectinload(cls.repository),
            selectinload(cls.classifications),
            selectinload(cls.tech_stacks)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_file_path(cls, session: AsyncSession, file_path: str, repository_id: int) -> Optional["Agent"]:
        """Get agent by file path and repository"""
        stmt = select(cls).where(
            and_(cls.file_path == file_path, cls.repository_id == repository_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def search_and_filter(
        cls, 
        session: AsyncSession,
        search: Optional[str] = None,
        lifecycle_phase: Optional[str] = None,
        role_type: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
        repository_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List["Agent"]:
        """Advanced search and filtering"""
        stmt = select(cls).options(
            selectinload(cls.repository),
            selectinload(cls.classifications),
            selectinload(cls.tech_stacks)
        )
        
        # Apply filters
        conditions = [cls.is_classified == True]
        
        if search:
            conditions.append(
                or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                    cls.system_prompt.ilike(f"%{search}%")
                )
            )
        
        if repository_id:
            conditions.append(cls.repository_id == repository_id)
        
        if lifecycle_phase:
            stmt = stmt.join(Classification).filter(
                Classification.lifecycle_phase == lifecycle_phase
            )
        
        if role_type:
            stmt = stmt.join(Classification).filter(
                Classification.role_type == role_type
            )
        
        if tech_stack:
            stmt = stmt.join(TechStack).filter(
                TechStack.tag.in_(tech_stack)
            )
        
        # Apply all conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Order by repository star count (popularity)
        stmt = stmt.join(Repository).order_by(Repository.star_count.desc())
        
        # Pagination
        stmt = stmt.offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        return result.scalars().unique().all()
    
    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        """Count total agents"""
        stmt = select(func.count(cls.id))
        result = await session.execute(stmt)
        return result.scalar()
    
    @classmethod
    async def count_classified(cls, session: AsyncSession) -> int:
        """Count classified agents"""
        stmt = select(func.count(cls.id)).where(cls.is_classified == True)
        result = await session.execute(stmt)
        return result.scalar()
    
    @classmethod
    async def get_unclassified(cls, session: AsyncSession, limit: int = 100) -> List["Agent"]:
        """Get unclassified agents for processing"""
        stmt = select(cls).where(
            and_(cls.is_parsed == True, cls.is_classified == False)
        ).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_popular(cls, session: AsyncSession, limit: int = 10) -> List["Agent"]:
        """Get popular agents by repository stars"""
        stmt = select(cls).options(
            selectinload(cls.repository),
            selectinload(cls.classifications)
        ).join(Repository).where(
            cls.is_classified == True
        ).order_by(
            Repository.star_count.desc()
        ).limit(limit)
        
        result = await session.execute(stmt)
        return result.scalars().unique().all()
    
    async def mark_parsed(self, session: AsyncSession, content_hash: str):
        """Mark agent as parsed"""
        self.is_parsed = True
        self.parsed_at = datetime.utcnow()
        self.content_hash = content_hash
        await session.flush()
    
    async def mark_classified(self, session: AsyncSession):
        """Mark agent as classified"""
        self.is_classified = True
        await session.flush()
    
    @property
    def primary_classification(self) -> Optional["Classification"]:
        """Get primary classification with highest confidence"""
        if not self.classifications:
            return None
        return max(self.classifications, key=lambda c: c.confidence_score)
    
    @property
    def tech_tags(self) -> List[str]:
        """Get all technology tags"""
        if not self.tech_stacks:
            return []
        return [ts.tag for ts in self.tech_stacks]
    
    def to_dict(self, include_content: bool = False) -> dict:
        """Convert to dictionary"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "file_path": self.file_path,
            "repository_id": self.repository_id,
            "is_parsed": self.is_parsed,
            "is_classified": self.is_classified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None
        }
        
        if include_content:
            data.update({
                "system_prompt": self.system_prompt,
                "yaml_metadata": self.yaml_metadata
            })
        
        if self.repository:
            data["repository"] = self.repository.to_dict()
        
        if self.classifications:
            data["classifications"] = [c.to_dict() for c in self.classifications]
        
        if self.tech_stacks:
            data["tech_stack"] = [ts.tag for ts in self.tech_stacks]
        
        return data


# Import models after class definition to avoid circular imports
from app.models.repository import Repository
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.models.download_selection import DownloadSelection