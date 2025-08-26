# Integration tests for API endpoints

import pytest
import json
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from app.core.database import Base, engine
from app.models.repository import Repository
from app.models.agent import Agent
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.models.download_selection import DownloadSelection


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
async def test_data(async_session: AsyncSession):
    """Create test data for API testing"""
    # Create repository
    repo = await Repository.create(
        async_session,
        name="test/api-agents",
        url="https://github.com/test/api-agents.git",
        description="Test repository for API testing",
        star_count=150,
        is_active=True
    )
    
    # Create agents
    agents_data = [
        {
            "name": "Backend Developer",
            "description": "Helps with backend development tasks using Python and FastAPI",
            "file_path": "agents/backend_dev.md",
            "system_prompt": "You are a backend developer. Help with server-side development.",
            "yaml_metadata": {"type": "developer", "experience": "senior"}
        },
        {
            "name": "Frontend Specialist", 
            "description": "Expert in React and modern frontend technologies",
            "file_path": "agents/frontend_spec.md",
            "system_prompt": "You are a frontend specialist. Help with client-side development.",
            "yaml_metadata": {"type": "specialist", "frameworks": ["React", "Vue"]}
        },
        {
            "name": "QA Tester",
            "description": "Quality assurance and testing expert",
            "file_path": "agents/qa_tester.md", 
            "system_prompt": "You are a QA tester. Help with testing and quality assurance.",
            "yaml_metadata": {"type": "tester", "tools": ["pytest", "selenium"]}
        }
    ]
    
    created_agents = []
    for i, agent_data in enumerate(agents_data):
        agent = await Agent.create(
            async_session,
            repository_id=repo.id,
            **agent_data
        )
        await agent.mark_parsed(async_session, f"hash_{i}")
        
        # Add classifications
        lifecycle_phases = ["development", "development", "testing"]
        role_types = ["backend-developer", "frontend-developer", "qa-tester"]
        
        classification = await Classification.create(
            async_session,
            agent_id=agent.id,
            lifecycle_phase=lifecycle_phases[i],
            role_type=role_types[i],
            confidence_score=0.9
        )
        
        # Add tech stacks
        tech_stacks = [
            [{"tag": "Python", "category": "programming-language"}, {"tag": "FastAPI", "category": "web-framework"}],
            [{"tag": "React", "category": "frontend-framework"}, {"tag": "JavaScript", "category": "programming-language"}],
            [{"tag": "Testing", "category": "general"}, {"tag": "Quality Assurance", "category": "general"}]
        ]
        
        await TechStack.create_multiple(async_session, agent.id, tech_stacks[i])
        await agent.mark_classified(async_session)
        created_agents.append(agent)
    
    await async_session.commit()
    return {"repository": repo, "agents": created_agents}


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAgentsAPI:
    """Test cases for agents API endpoints"""
    
    def test_search_agents_basic(self, client: TestClient, test_data):
        """Test basic agent search functionality"""
        response = client.get("/api/agents/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "agents" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_next" in data
        
        assert len(data["agents"]) >= 3  # At least our test agents
        assert data["total"] >= 3
    
    def test_search_agents_with_filters(self, client: TestClient, test_data):
        """Test agent search with filters"""
        # Test lifecycle filter
        response = client.get("/api/agents/?lifecycle=development")
        assert response.status_code == 200
        data = response.json()
        
        # Should return backend and frontend developers
        assert len(data["agents"]) >= 2
        for agent in data["agents"]:
            if agent.get("classifications"):
                assert agent["classifications"]["lifecycle_phase"] == "development"
    
    def test_search_agents_with_search_query(self, client: TestClient, test_data):
        """Test agent search with text query"""
        response = client.get("/api/agents/?search=backend")
        assert response.status_code == 200
        data = response.json()
        
        # Should find the backend developer
        assert len(data["agents"]) >= 1
        backend_agent = next((a for a in data["agents"] if "backend" in a["name"].lower()), None)
        assert backend_agent is not None
    
    def test_search_agents_with_role_filter(self, client: TestClient, test_data):
        """Test agent search with role filter"""
        response = client.get("/api/agents/?role=qa-tester")
        assert response.status_code == 200
        data = response.json()
        
        # Should find the QA tester
        assert len(data["agents"]) >= 1
        qa_agent = next((a for a in data["agents"] if a.get("classifications", {}).get("role_type") == "qa-tester"), None)
        assert qa_agent is not None
    
    def test_search_agents_pagination(self, client: TestClient, test_data):
        """Test agent search pagination"""
        # Test first page
        response = client.get("/api/agents/?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["agents"]) <= 2
        assert data["page"] == 1
        assert data["limit"] == 2
        
        # Test second page if enough agents
        if data["total"] > 2:
            response = client.get("/api/agents/?limit=2&offset=2")
            assert response.status_code == 200
            data2 = response.json()
            assert data2["page"] == 2
    
    def test_get_agent_detail(self, client: TestClient, test_data):
        """Test getting agent detail"""
        agent = test_data["agents"][0]
        
        response = client.get(f"/api/agents/{agent.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == agent.id
        assert data["name"] == agent.name
        assert data["description"] == agent.description
        assert "system_prompt" in data
        assert "yaml_metadata" in data
        assert "classifications" in data
        assert "tech_stack" in data
        assert "repository" in data
    
    def test_get_agent_detail_not_found(self, client: TestClient):
        """Test getting non-existent agent"""
        response = client.get("/api/agents/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_related_agents(self, client: TestClient, test_data):
        """Test getting related agents"""
        agent = test_data["agents"][0]
        
        response = client.get(f"/api/agents/{agent.id}/related")
        assert response.status_code == 200
        data = response.json()
        
        assert "related_agents" in data
        # Related agents list can be empty if no similarities found
        assert isinstance(data["related_agents"], list)
    
    def test_get_popular_agents(self, client: TestClient, test_data):
        """Test getting popular agents"""
        response = client.get("/api/agents/popular/trending")
        assert response.status_code == 200
        data = response.json()
        
        assert "popular_agents" in data
        assert isinstance(data["popular_agents"], list)
    
    def test_compare_agents(self, client: TestClient, test_data):
        """Test agent comparison"""
        agent_ids = [agent.id for agent in test_data["agents"][:2]]
        
        response = client.post(
            "/api/agents/compare",
            json={"agent_ids": agent_ids}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "agents" in data
        assert "comparison_insights" in data
        assert len(data["agents"]) == 2
        
        # Check comparison insights structure
        insights = data["comparison_insights"]
        assert "shared_technologies" in insights
        assert "unique_technologies" in insights
        assert "complexity_levels" in insights
        assert "recommendations" in insights
    
    def test_compare_agents_invalid_request(self, client: TestClient):
        """Test agent comparison with invalid request"""
        # Test with too few agents
        response = client.post(
            "/api/agents/compare",
            json={"agent_ids": [1]}
        )
        assert response.status_code == 422  # Validation error
        
        # Test with non-existent agents
        response = client.post(
            "/api/agents/compare", 
            json={"agent_ids": [99999, 99998]}
        )
        assert response.status_code == 404


class TestRepositoriesAPI:
    """Test cases for repositories API endpoints"""
    
    def test_list_repositories(self, client: TestClient, test_data):
        """Test listing repositories"""
        response = client.get("/api/repositories/")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1  # At least our test repository
        
        # Check repository structure
        repo = data[0]
        required_fields = ["id", "name", "url", "description", "star_count", "is_active"]
        for field in required_fields:
            assert field in repo
    
    def test_get_repository_stats(self, client: TestClient, test_data):
        """Test getting repository statistics"""
        response = client.get("/api/repositories/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_repositories" in data
        assert "active_repositories" in data
        assert "total_agents" in data
        assert "last_sync_summary" in data
        
        assert data["total_repositories"] >= 1
        assert data["total_agents"] >= 3
    
    def test_get_repository_agents(self, client: TestClient, test_data):
        """Test getting agents from specific repository"""
        repo = test_data["repository"]
        
        response = client.get(f"/api/repositories/{repo.id}/agents")
        assert response.status_code == 200
        data = response.json()
        
        assert "repository" in data
        assert "agents" in data
        assert "total" in data
        
        assert data["repository"]["id"] == repo.id
        assert len(data["agents"]) == 3  # Our test agents
    
    def test_get_repository_agents_not_found(self, client: TestClient):
        """Test getting agents from non-existent repository"""
        response = client.get("/api/repositories/99999/agents")
        assert response.status_code == 404


class TestDownloadsAPI:
    """Test cases for downloads API endpoints"""
    
    def test_add_to_selection(self, client: TestClient, test_data):
        """Test adding agent to download selection"""
        agent = test_data["agents"][0]
        session_id = "test_session_123"
        
        response = client.post(
            "/api/downloads/selection/add",
            json={
                "session_id": session_id,
                "agent_id": agent.id
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["selection_count"] == 1
        assert agent.name in data["message"]
    
    def test_add_to_selection_agent_not_found(self, client: TestClient):
        """Test adding non-existent agent to selection"""
        response = client.post(
            "/api/downloads/selection/add",
            json={
                "session_id": "test_session",
                "agent_id": 99999
            }
        )
        assert response.status_code == 404
    
    def test_remove_from_selection(self, client: TestClient, test_data):
        """Test removing agent from download selection"""
        agent = test_data["agents"][0]
        session_id = "test_session_456"
        
        # First add to selection
        client.post(
            "/api/downloads/selection/add",
            json={
                "session_id": session_id,
                "agent_id": agent.id
            }
        )
        
        # Then remove
        response = client.post(
            "/api/downloads/selection/remove",
            json={
                "session_id": session_id,
                "agent_id": agent.id
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["selection_count"] == 0
    
    def test_get_selection(self, client: TestClient, test_data):
        """Test getting current selection"""
        session_id = "test_session_789"
        
        # Add some agents to selection
        for agent in test_data["agents"][:2]:
            client.post(
                "/api/downloads/selection/add",
                json={
                    "session_id": session_id,
                    "agent_id": agent.id
                }
            )
        
        # Get selection
        response = client.get(f"/api/downloads/selection/{session_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert len(data["selected_agents"]) == 2
        assert data["total_selected"] == 2
    
    def test_clear_selection(self, client: TestClient, test_data):
        """Test clearing selection"""
        session_id = "test_session_clear"
        
        # Add agent to selection
        agent = test_data["agents"][0]
        client.post(
            "/api/downloads/selection/add",
            json={
                "session_id": session_id,
                "agent_id": agent.id
            }
        )
        
        # Clear selection
        response = client.post(f"/api/downloads/selection/clear?session_id={session_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["selection_count"] == 0
    
    def test_bulk_download(self, client: TestClient, test_data):
        """Test bulk download functionality"""
        agent_ids = [agent.id for agent in test_data["agents"][:2]]
        
        response = client.post(
            "/api/downloads/package/bulk",
            json={
                "agent_ids": agent_ids,
                "include_readme": True,
                "package_name": "test_package"
            }
        )
        assert response.status_code == 200
        
        # Check that we get a ZIP file
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert "test_package.zip" in response.headers["content-disposition"]
        
        # Check that response has content
        assert len(response.content) > 0
    
    def test_bulk_download_agent_not_found(self, client: TestClient):
        """Test bulk download with non-existent agent"""
        response = client.post(
            "/api/downloads/package/bulk",
            json={
                "agent_ids": [99999],
                "include_readme": True
            }
        )
        assert response.status_code == 404
    
    def test_get_download_stats(self, client: TestClient, test_data):
        """Test getting download statistics"""
        response = client.get("/api/downloads/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "popular_agents" in data
        assert "recent_downloads" in data
        assert "total_packages_generated" in data
        
        assert isinstance(data["popular_agents"], list)
        assert isinstance(data["recent_downloads"], int)
        assert isinstance(data["total_packages_generated"], int)


@pytest.mark.asyncio
class TestAPIIntegration:
    """Integration tests for complete API workflows"""
    
    async def test_complete_discovery_workflow(self, client: TestClient, test_data):
        """Test complete agent discovery and download workflow"""
        # 1. Search for agents
        response = client.get("/api/agents/?search=backend")
        assert response.status_code == 200
        search_data = response.json()
        assert len(search_data["agents"]) >= 1
        
        # 2. Get agent details
        agent = search_data["agents"][0]
        response = client.get(f"/api/agents/{agent['id']}")
        assert response.status_code == 200
        detail_data = response.json()
        
        # 3. Find related agents
        response = client.get(f"/api/agents/{agent['id']}/related")
        assert response.status_code == 200
        
        # 4. Add to selection
        session_id = "workflow_test_session"
        response = client.post(
            "/api/downloads/selection/add",
            json={
                "session_id": session_id,
                "agent_id": agent["id"]
            }
        )
        assert response.status_code == 200
        
        # 5. Compare agents (if multiple)
        if len(search_data["agents"]) >= 2:
            agent_ids = [a["id"] for a in search_data["agents"][:2]]
            response = client.post(
                "/api/agents/compare",
                json={"agent_ids": agent_ids}
            )
            assert response.status_code == 200
        
        # 6. Download package
        response = client.post(
            "/api/downloads/package/bulk",
            json={
                "agent_ids": [agent["id"]],
                "include_readme": True,
                "package_name": "workflow_test"
            }
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
    
    def test_api_error_handling(self, client: TestClient):
        """Test API error handling"""
        # Test invalid agent ID
        response = client.get("/api/agents/invalid")
        assert response.status_code == 422  # Validation error
        
        # Test invalid JSON
        response = client.post(
            "/api/agents/compare",
            data="invalid json"
        )
        assert response.status_code == 422
        
        # Test missing required fields
        response = client.post(
            "/api/downloads/selection/add",
            json={"session_id": "test"}  # Missing agent_id
        )
        assert response.status_code == 422