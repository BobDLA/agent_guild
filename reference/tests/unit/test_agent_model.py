# Unit tests for Agent model

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.repository import Repository
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.core.database import Base, engine


@pytest.fixture
async def async_session():
    """Create async session for testing"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_repository(async_session: AsyncSession):
    """Create a sample repository for testing"""
    repo = await Repository.create(
        async_session,
        name="test/sample-repo",
        url="https://github.com/test/sample-repo.git",
        description="Sample repository for testing",
        star_count=100
    )
    await async_session.commit()
    return repo


@pytest.fixture
async def sample_agent(async_session: AsyncSession, sample_repository: Repository):
    """Create a sample agent for testing"""
    agent = await Agent.create(
        async_session,
        name="Test Agent",
        description="A test agent for unit testing",
        file_path="agents/test_agent.md",
        repository_id=sample_repository.id,
        system_prompt="You are a test agent. Help with testing tasks.",
        yaml_metadata={"type": "test", "version": "1.0"}
    )
    await agent.mark_parsed(async_session, "test_hash_123")
    await async_session.commit()
    return agent


class TestAgentModel:
    """Test cases for Agent model"""

    async def test_agent_creation(self, async_session: AsyncSession, sample_repository: Repository):
        """Test creating a new agent"""
        agent = await Agent.create(
            async_session,
            name="New Test Agent",
            description="Testing agent creation",
            file_path="agents/new_test.md",
            repository_id=sample_repository.id,
            system_prompt="Test prompt",
            yaml_metadata={"test": True}
        )
        
        assert agent.id is not None
        assert agent.name == "New Test Agent"
        assert agent.description == "Testing agent creation"
        assert agent.repository_id == sample_repository.id
        assert agent.is_parsed is False
        assert agent.is_classified is False

    async def test_agent_get_by_id(self, async_session: AsyncSession, sample_agent: Agent):
        """Test retrieving agent by ID"""
        retrieved_agent = await Agent.get_by_id(async_session, sample_agent.id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.id == sample_agent.id
        assert retrieved_agent.name == sample_agent.name
        assert retrieved_agent.repository is not None

    async def test_agent_get_by_file_path(self, async_session: AsyncSession, sample_agent: Agent):
        """Test retrieving agent by file path and repository"""
        retrieved_agent = await Agent.get_by_file_path(
            async_session, 
            sample_agent.file_path, 
            sample_agent.repository_id
        )
        
        assert retrieved_agent is not None
        assert retrieved_agent.id == sample_agent.id

    async def test_agent_mark_parsed(self, async_session: AsyncSession, sample_repository: Repository):
        """Test marking agent as parsed"""
        agent = await Agent.create(
            async_session,
            name="Parse Test Agent",
            description="Testing parse marking",
            file_path="agents/parse_test.md",
            repository_id=sample_repository.id
        )
        
        assert agent.is_parsed is False
        assert agent.content_hash is None
        
        await agent.mark_parsed(async_session, "parsed_hash_456")
        
        assert agent.is_parsed is True
        assert agent.content_hash == "parsed_hash_456"
        assert agent.parsed_at is not None

    async def test_agent_mark_classified(self, async_session: AsyncSession, sample_agent: Agent):
        """Test marking agent as classified"""
        assert sample_agent.is_classified is False
        
        await sample_agent.mark_classified(async_session)
        
        assert sample_agent.is_classified is True

    async def test_agent_search_and_filter(self, async_session: AsyncSession, sample_repository: Repository):
        """Test agent search and filtering functionality"""
        # Create multiple test agents
        agents_data = [
            {
                "name": "Backend Agent",
                "description": "Backend development helper",
                "file_path": "agents/backend.md"
            },
            {
                "name": "Frontend Agent", 
                "description": "Frontend development assistant",
                "file_path": "agents/frontend.md"
            },
            {
                "name": "Testing Agent",
                "description": "Testing and QA helper",
                "file_path": "agents/testing.md"
            }
        ]
        
        created_agents = []
        for agent_data in agents_data:
            agent = await Agent.create(
                async_session,
                repository_id=sample_repository.id,
                **agent_data
            )
            await agent.mark_parsed(async_session, f"hash_{agent.name}")
            await agent.mark_classified(async_session)
            created_agents.append(agent)
        
        await async_session.commit()
        
        # Test search by name
        results = await Agent.search_and_filter(
            async_session,
            search="Backend",
            limit=10
        )
        assert len(results) >= 1
        assert any(agent.name == "Backend Agent" for agent in results)
        
        # Test filtering by repository
        results = await Agent.search_and_filter(
            async_session,
            repository_id=sample_repository.id,
            limit=10
        )
        assert len(results) >= 3  # At least our 3 test agents

    async def test_agent_count_methods(self, async_session: AsyncSession, sample_agent: Agent):
        """Test agent counting methods"""
        total_count = await Agent.count(async_session)
        assert total_count >= 1
        
        # Mark agent as classified for classified count test
        await sample_agent.mark_classified(async_session)
        await async_session.commit()
        
        classified_count = await Agent.count_classified(async_session)
        assert classified_count >= 1

    async def test_agent_get_unclassified(self, async_session: AsyncSession, sample_repository: Repository):
        """Test getting unclassified agents"""
        # Create an unclassified agent
        agent = await Agent.create(
            async_session,
            name="Unclassified Agent",
            description="Not yet classified",
            file_path="agents/unclassified.md",
            repository_id=sample_repository.id
        )
        await agent.mark_parsed(async_session, "unclassified_hash")
        await async_session.commit()
        
        unclassified = await Agent.get_unclassified(async_session, limit=10)
        assert len(unclassified) >= 1
        assert any(a.id == agent.id for a in unclassified)

    async def test_agent_with_classification(self, async_session: AsyncSession, sample_agent: Agent):
        """Test agent with classification relationship"""
        # Add classification
        classification = await Classification.create(
            async_session,
            agent_id=sample_agent.id,
            lifecycle_phase="development",
            role_type="backend-developer",
            confidence_score=0.95
        )
        await async_session.commit()
        
        # Retrieve agent and check classification
        agent = await Agent.get_by_id(async_session, sample_agent.id)
        assert agent.primary_classification is not None
        assert agent.primary_classification.lifecycle_phase == "development"
        assert agent.primary_classification.role_type == "backend-developer"

    async def test_agent_with_tech_stack(self, async_session: AsyncSession, sample_agent: Agent):
        """Test agent with tech stack relationship"""
        # Add tech stack
        tech_stacks = [
            {"tag": "Python", "category": "programming-language"},
            {"tag": "FastAPI", "category": "web-framework"},
            {"tag": "Testing", "category": "general"}
        ]
        
        await TechStack.create_multiple(async_session, sample_agent.id, tech_stacks)
        await async_session.commit()
        
        # Retrieve agent and check tech stack
        agent = await Agent.get_by_id(async_session, sample_agent.id)
        assert len(agent.tech_tags) == 3
        assert "Python" in agent.tech_tags
        assert "FastAPI" in agent.tech_tags
        assert "Testing" in agent.tech_tags

    async def test_agent_to_dict(self, async_session: AsyncSession, sample_agent: Agent):
        """Test agent serialization to dictionary"""
        agent_dict = sample_agent.to_dict()
        
        assert isinstance(agent_dict, dict)
        assert agent_dict["id"] == sample_agent.id
        assert agent_dict["name"] == sample_agent.name
        assert agent_dict["description"] == sample_agent.description
        assert agent_dict["file_path"] == sample_agent.file_path
        assert agent_dict["is_parsed"] == sample_agent.is_parsed
        assert agent_dict["is_classified"] == sample_agent.is_classified
        
        # Test with content included
        agent_dict_with_content = sample_agent.to_dict(include_content=True)
        assert "system_prompt" in agent_dict_with_content
        assert "yaml_metadata" in agent_dict_with_content

    async def test_agent_repository_relationship(self, async_session: AsyncSession, sample_agent: Agent):
        """Test agent-repository relationship"""
        agent = await Agent.get_by_id(async_session, sample_agent.id)
        
        assert agent.repository is not None
        assert agent.repository.name == "test/sample-repo"
        assert agent.repository_id == agent.repository.id

    async def test_agent_update_existing(self, async_session: AsyncSession, sample_agent: Agent):
        """Test updating existing agent content"""
        original_name = sample_agent.name
        original_hash = sample_agent.content_hash
        
        # Simulate content update
        sample_agent.name = "Updated Test Agent"
        sample_agent.description = "Updated description"
        sample_agent.is_classified = False  # Reset classification
        
        await sample_agent.mark_parsed(async_session, "new_hash_789")
        await async_session.commit()
        
        # Verify updates
        updated_agent = await Agent.get_by_id(async_session, sample_agent.id)
        assert updated_agent.name == "Updated Test Agent"
        assert updated_agent.description == "Updated description"
        assert updated_agent.content_hash == "new_hash_789"
        assert updated_agent.content_hash != original_hash
        assert updated_agent.is_classified is False


@pytest.mark.asyncio
class TestAgentIntegration:
    """Integration tests for Agent model with related models"""
    
    async def test_agent_full_workflow(self, async_session: AsyncSession, sample_repository: Repository):
        """Test complete agent processing workflow"""
        # 1. Create agent
        agent = await Agent.create(
            async_session,
            name="Workflow Test Agent",
            description="Testing complete workflow",
            file_path="agents/workflow_test.md",
            repository_id=sample_repository.id,
            system_prompt="Complete workflow test prompt",
            yaml_metadata={"workflow": "test"}
        )
        
        # 2. Mark as parsed
        await agent.mark_parsed(async_session, "workflow_hash")
        
        # 3. Add classification
        classification = await Classification.create(
            async_session,
            agent_id=agent.id,
            lifecycle_phase="testing",
            role_type="qa-tester",
            confidence_score=0.88
        )
        
        # 4. Add tech stack
        tech_stacks = [
            {"tag": "Pytest", "category": "testing"},
            {"tag": "Quality Assurance", "category": "general"}
        ]
        await TechStack.create_multiple(async_session, agent.id, tech_stacks)
        
        # 5. Mark as classified
        await agent.mark_classified(async_session)
        await async_session.commit()
        
        # 6. Verify complete agent
        final_agent = await Agent.get_by_id(async_session, agent.id)
        
        assert final_agent.is_parsed is True
        assert final_agent.is_classified is True
        assert final_agent.primary_classification is not None
        assert final_agent.primary_classification.lifecycle_phase == "testing"
        assert len(final_agent.tech_tags) == 2
        assert "Pytest" in final_agent.tech_tags
        
        # 7. Test search functionality
        search_results = await Agent.search_and_filter(
            async_session,
            lifecycle_phase="testing",
            role_type="qa-tester",
            limit=10
        )
        
        assert len(search_results) >= 1
        assert any(a.id == agent.id for a in search_results)