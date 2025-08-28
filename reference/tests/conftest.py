# Test configuration and fixtures

import pytest
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

# Set test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_subagent_guild.db"
os.environ["DEBUG"] = "true"

# Import after setting environment
from app.core.database import Base, engine, AsyncSessionLocal
from app.models import Repository, Agent, Classification, TechStack, DownloadSelection


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_database():
    """Set up test database"""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Remove test database file
    test_db_path = Path("test_subagent_guild.db")
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
async def db_session(setup_test_database) -> AsyncGenerator:
    """Provide a database session for testing"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def clean_db(db_session):
    """Clean database before each test"""
    # Clean up all tables in reverse order to handle foreign keys
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()
    yield db_session


@pytest.fixture
def sample_repository_data():
    """Sample repository data for testing"""
    return {
        "name": "test/sample-agents",
        "url": "https://github.com/test/sample-agents.git",
        "description": "Sample repository for testing",
        "star_count": 42,
        "language": "Markdown",
        "is_active": True
    }


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        "name": "Test Development Agent",
        "description": "A comprehensive agent for development tasks",
        "file_path": "agents/development_agent.md",
        "system_prompt": """You are a development agent. Your role is to assist with software development tasks.

Key capabilities:
- Code generation and review
- Architecture planning
- Best practices guidance
- Problem solving

Always provide clear, actionable advice.""",
        "yaml_metadata": {
            "type": "development",
            "complexity": "intermediate",
            "tags": ["development", "coding", "architecture"],
            "version": "1.0"
        }
    }


@pytest.fixture
def sample_classification_data():
    """Sample classification data for testing"""
    return {
        "lifecycle_phase": "development",
        "role_type": "backend-developer",
        "confidence_score": 0.92,
        "is_ai_generated": True
    }


@pytest.fixture
def sample_tech_stack_data():
    """Sample tech stack data for testing"""
    return [
        {"tag": "Python", "category": "programming-language"},
        {"tag": "FastAPI", "category": "web-framework"},
        {"tag": "Testing", "category": "general"},
        {"tag": "Architecture", "category": "system-design"}
    ]


@pytest.fixture
async def test_repository(clean_db, sample_repository_data):
    """Create a test repository"""
    repo = await Repository.create(clean_db, **sample_repository_data)
    await clean_db.commit()
    return repo


@pytest.fixture
async def test_agent(clean_db, test_repository, sample_agent_data):
    """Create a test agent"""
    agent = await Agent.create(
        clean_db,
        repository_id=test_repository.id,
        **sample_agent_data
    )
    await agent.mark_parsed(clean_db, "test_content_hash")
    await clean_db.commit()
    return agent


@pytest.fixture
async def classified_test_agent(clean_db, test_agent, sample_classification_data, sample_tech_stack_data):
    """Create a fully classified test agent"""
    # Add classification
    classification = await Classification.create(
        clean_db,
        agent_id=test_agent.id,
        **sample_classification_data
    )
    
    # Add tech stack
    await TechStack.create_multiple(clean_db, test_agent.id, sample_tech_stack_data)
    
    # Mark as classified
    await test_agent.mark_classified(clean_db)
    await clean_db.commit()
    
    return test_agent


@pytest.fixture
def mock_file_system(tmp_path):
    """Create a mock file system structure for testing"""
    # Create repository structure
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Create agents directory
    agents_dir = repo_dir / "agents"
    agents_dir.mkdir()
    
    # Create sample agent files
    agent_files = {
        "backend_agent.md": """---
name: "Backend Development Agent"
description: "Specialized in server-side development"
role: "backend-developer"
tags: ["backend", "api", "database"]
---

# Backend Development Agent

You are a backend development specialist...

## System Prompt

```
You are an expert backend developer. Help with:
- API design and implementation
- Database schema design
- Server architecture
- Performance optimization
```
""",
        "frontend_agent.md": """---
name: "Frontend UI Agent"
description: "Expert in user interface development"
role: "frontend-developer"
tags: ["frontend", "ui", "react"]
---

# Frontend UI Agent

You specialize in creating beautiful user interfaces...
""",
        "testing_agent.md": """# Testing Agent

You are a testing specialist. Help with quality assurance and test automation.
"""
    }
    
    for filename, content in agent_files.items():
        with open(agents_dir / filename, "w") as f:
            f.write(content)
    
    # Create non-agent files (should be filtered out)
    with open(repo_dir / "README.md", "w") as f:
        f.write("# Test Repository\n\nThis is a test repository.")
    
    with open(repo_dir / "LICENSE.md", "w") as f:
        f.write("MIT License")
    
    return repo_dir


@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content for parsing tests"""
    return """---
name: "System Architecture Agent"
description: "Expert in designing scalable system architectures"
role: "system-architect"
complexity: "advanced"
tags: ["architecture", "scalability", "design-patterns"]
version: "2.1"
author: "System Design Team"
---

# System Architecture Agent

You are an expert system architect with deep knowledge of scalable system design.

## Capabilities

- Microservices architecture design
- Database schema optimization
- Load balancing strategies
- Caching implementation
- Security architecture

## System Prompt

```
You are a senior system architect with 10+ years of experience.

Your role is to help design and review system architectures for web applications.

Key focus areas:
1. Scalability and performance
2. Security and reliability
3. Maintainability and extensibility
4. Cost optimization
5. Technology selection

Always consider:
- Current system requirements
- Future growth projections
- Team capabilities
- Technology constraints
- Budget limitations

Provide detailed architectural diagrams and implementation guides.
```

## Usage Examples

Perfect for:
- Large-scale system design
- Architecture reviews
- Technology stack selection
- Performance optimization planning
- Security architecture planning
"""


# Testing utilities
class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def assert_agent_dict_structure(agent_dict, include_content=False):
        """Assert that agent dictionary has correct structure"""
        required_fields = [
            "id", "name", "description", "file_path", "repository_id",
            "is_parsed", "is_classified", "created_at"
        ]
        
        for field in required_fields:
            assert field in agent_dict, f"Missing field: {field}"
        
        if include_content:
            content_fields = ["system_prompt", "yaml_metadata"]
            for field in content_fields:
                assert field in agent_dict, f"Missing content field: {field}"
    
    @staticmethod
    def assert_classification_structure(classification_dict):
        """Assert that classification dictionary has correct structure"""
        required_fields = [
            "id", "agent_id", "lifecycle_phase", "role_type",
            "confidence_score", "is_ai_generated", "classified_at"
        ]
        
        for field in required_fields:
            assert field in classification_dict, f"Missing classification field: {field}"
    
    @staticmethod
    def create_mock_claude_response(lifecycle_phase="development", role_type="general", confidence=0.8):
        """Create mock Claude API response"""
        return {
            "lifecycle_phase": lifecycle_phase,
            "role_type": role_type,
            "confidence_score": confidence,
            "tech_stack": [
                {"tag": "General", "category": "general"}
            ],
            "reasoning": "Mock classification for testing",
            "keywords_found": ["test", "mock"]
        }


# Make test utilities available
@pytest.fixture
def test_utils():
    """Provide test utilities"""
    return TestUtils