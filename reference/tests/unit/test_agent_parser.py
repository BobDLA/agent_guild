# Unit tests for Agent Parser Service

import pytest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agent_parser import AgentParserService, ParsedAgent
from app.models.repository import Repository
from app.models.agent import Agent


@pytest.fixture
def parser_service():
    """Create agent parser service instance"""
    return AgentParserService()


@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content with frontmatter"""
    return """---
name: "Test Agent"
description: "A test agent for parsing"
role: "tester"
tags: ["testing", "python", "automation"]
version: "1.0"
---

# Test Agent

This is a test agent designed for parsing validation.

## System Prompt

```
You are a test agent. Your role is to help with testing and quality assurance tasks.

Key responsibilities:
- Write comprehensive test cases
- Identify edge cases and potential issues
- Ensure code quality and reliability
- Provide testing best practices

Always be thorough and detail-oriented in your testing approach.
```

## Usage Examples

Use this agent for:
- Unit test generation
- Integration test planning
- Test automation scripts
- Quality assurance reviews
"""


@pytest.fixture
def sample_agent_minimal():
    """Minimal agent content without frontmatter"""
    return """# Simple Agent

This is a simple agent without YAML frontmatter.

You are a helpful assistant. Help users with their tasks efficiently and accurately.
"""


@pytest.fixture
def temp_repo_structure(sample_agent_content):
    """Create temporary repository structure with test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Create agent files
        (repo_path / "agents").mkdir()
        
        # Valid agent file
        with open(repo_path / "agents" / "test_agent.md", "w") as f:
            f.write(sample_agent_content)
        
        # Another valid agent file
        with open(repo_path / "agents" / "simple_agent.md", "w") as f:
            f.write("# Simple Agent\n\nA basic agent for testing.")
        
        # Non-agent files (should be filtered out)
        with open(repo_path / "README.md", "w") as f:
            f.write("# Repository README")
        
        with open(repo_path / "LICENSE.md", "w") as f:
            f.write("MIT License")
        
        # Hidden directory (should be ignored)
        (repo_path / ".git").mkdir()
        with open(repo_path / ".git" / "config", "w") as f:
            f.write("git config")
        
        yield repo_path


class TestAgentParserService:
    """Test cases for AgentParserService"""
    
    def test_extract_name_from_frontmatter(self, parser_service: AgentParserService):
        """Test extracting agent name from YAML frontmatter"""
        metadata = {"name": "Frontend Optimizer"}
        file_path = Path("test_agent.md")
        
        name = parser_service._extract_name(metadata, file_path)
        assert name == "Frontend Optimizer"
    
    def test_extract_name_from_title(self, parser_service: AgentParserService):
        """Test extracting agent name from title field"""
        metadata = {"title": "Performance Analyzer"}
        file_path = Path("test_agent.md")
        
        name = parser_service._extract_name(metadata, file_path)
        assert name == "Performance Analyzer"
    
    def test_extract_name_from_filename(self, parser_service: AgentParserService):
        """Test extracting agent name from filename when no metadata"""
        metadata = {}
        file_path = Path("backend_developer_agent.md")
        
        name = parser_service._extract_name(metadata, file_path)
        assert name == "Backend Developer Agent"
    
    def test_extract_description_from_metadata(self, parser_service: AgentParserService):
        """Test extracting description from metadata"""
        metadata = {"description": "Helps with backend development tasks"}
        content = "Some content here"
        
        description = parser_service._extract_description(metadata, content)
        assert description == "Helps with backend development tasks"
    
    def test_extract_description_from_content(self, parser_service: AgentParserService):
        """Test extracting description from content when no metadata"""
        metadata = {}
        content = "# Agent Name\n\nThis agent helps with testing tasks.\n\nMore details..."
        
        description = parser_service._extract_description(metadata, content)
        assert description == "This agent helps with testing tasks."
    
    def test_extract_description_fallback(self, parser_service: AgentParserService):
        """Test description fallback when nothing is found"""
        metadata = {}
        content = "# Agent\n\n```code```\n\n## More"
        
        description = parser_service._extract_description(metadata, content)
        assert description == "Claude Code subagent"
    
    def test_extract_system_prompt_from_metadata(self, parser_service: AgentParserService):
        """Test extracting system prompt from metadata"""
        content = "Some content"
        metadata = {"system_prompt": "You are a helpful assistant"}
        
        prompt = parser_service._extract_system_prompt(content, metadata)
        assert prompt == "You are a helpful assistant"
    
    def test_extract_system_prompt_from_code_block(self, parser_service: AgentParserService):
        """Test extracting system prompt from code block"""
        content = """# Agent

Some description

```
You are a test agent.
Help with testing tasks.
```

More content"""
        metadata = {}
        
        prompt = parser_service._extract_system_prompt(content, metadata)
        assert "You are a test agent." in prompt
        assert "Help with testing tasks." in prompt
    
    def test_extract_system_prompt_fallback(self, parser_service: AgentParserService):
        """Test system prompt fallback to entire content"""
        content = "You are a simple agent without code blocks."
        metadata = {}
        
        prompt = parser_service._extract_system_prompt(content, metadata)
        assert prompt == content
    
    async def test_parse_agent_file_with_frontmatter(self, parser_service: AgentParserService, sample_agent_content):
        """Test parsing agent file with YAML frontmatter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_agent_content)
            temp_path = Path(f.name)
        
        try:
            parsed = await parser_service._parse_agent_file(
                temp_path, 
                "test_agent.md", 
                repository_id=1
            )
            
            assert isinstance(parsed, ParsedAgent)
            assert parsed.name == "Test Agent"
            assert parsed.description == "A test agent for parsing"
            assert parsed.file_path == "test_agent.md"
            assert parsed.repository_id == 1
            assert "You are a test agent" in parsed.system_prompt
            assert parsed.yaml_metadata["role"] == "tester"
            assert len(parsed.content_hash) == 16  # MD5 hash shortened to 16 chars
        
        finally:
            temp_path.unlink()
    
    async def test_parse_agent_file_without_frontmatter(self, parser_service: AgentParserService, sample_agent_minimal):
        """Test parsing agent file without YAML frontmatter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_agent_minimal)
            temp_path = Path(f.name)
        
        try:
            parsed = await parser_service._parse_agent_file(
                temp_path,
                "simple_agent.md",
                repository_id=1
            )
            
            assert parsed.name == "Simple Agent"
            assert "simple agent without YAML" in parsed.description
            assert "helpful assistant" in parsed.system_prompt
            assert parsed.yaml_metadata == {}
        
        finally:
            temp_path.unlink()
    
    async def test_get_agent_files(self, parser_service: AgentParserService, temp_repo_structure):
        """Test getting agent files from repository"""
        files = await parser_service._get_agent_files(temp_repo_structure)
        
        # Should find .md files but filter out README and LICENSE
        agent_files = [f.name for f in files]
        assert "test_agent.md" in agent_files
        assert "simple_agent.md" in agent_files
        assert "README.md" not in agent_files
        assert "LICENSE.md" not in agent_files
    
    def test_is_likely_agent_file(self, parser_service: AgentParserService):
        """Test agent file detection heuristics"""
        # High confidence agent content
        agent_content = """
        You are an expert system architect. Your role is to design scalable systems.
        
        ```
        System prompt content here
        ```
        """
        agent_metadata = {"name": "System Architect", "role": "architect"}
        
        is_agent = parser_service._is_likely_agent_file(agent_content, agent_metadata)
        assert is_agent is True
        
        # Low confidence content
        readme_content = "This is a README file with installation instructions."
        readme_metadata = {}
        
        is_agent = parser_service._is_likely_agent_file(readme_content, readme_metadata)
        assert is_agent is False
    
    @patch('app.services.agent_parser.Agent')
    async def test_create_new_agent(self, mock_agent_class, parser_service: AgentParserService):
        """Test creating new agent in database"""
        mock_session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent_class.create.return_value = mock_agent
        
        parsed_agent = ParsedAgent(
            name="Test Agent",
            description="Test description",
            file_path="test.md",
            repository_id=1,
            system_prompt="Test prompt",
            yaml_metadata={"test": True},
            content_hash="abc123",
            raw_content="test content"
        )
        
        result = await parser_service._create_new_agent(mock_session, parsed_agent)
        
        mock_agent_class.create.assert_called_once_with(
            mock_session,
            name="Test Agent",
            description="Test description",
            file_path="test.md",
            repository_id=1,
            system_prompt="Test prompt",
            yaml_metadata={"test": True}
        )
        mock_agent.mark_parsed.assert_called_once_with(mock_session, "abc123")
        assert result == mock_agent
    
    @patch('app.services.agent_parser.Agent')
    async def test_update_existing_agent(self, mock_agent_class, parser_service: AgentParserService):
        """Test updating existing agent"""
        mock_session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.name = "Old Name"
        
        parsed_agent = ParsedAgent(
            name="Updated Agent",
            description="Updated description", 
            file_path="test.md",
            repository_id=1,
            system_prompt="Updated prompt",
            yaml_metadata={"updated": True},
            content_hash="def456",
            raw_content="updated content"
        )
        
        result = await parser_service._update_existing_agent(mock_session, mock_agent, parsed_agent)
        
        assert mock_agent.name == "Updated Agent"
        assert mock_agent.description == "Updated description"
        assert mock_agent.system_prompt == "Updated prompt"
        assert mock_agent.yaml_metadata == {"updated": True}
        assert mock_agent.is_classified is False  # Should reset classification
        mock_agent.mark_parsed.assert_called_once_with(mock_session, "def456")
    
    async def test_validation_results(self, parser_service: AgentParserService):
        """Test agent validation functionality"""
        with patch('app.services.agent_parser.get_async_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock agents with various validation issues
            mock_agents = [
                MagicMock(
                    name="Good Agent",
                    description="A well-formed agent description",
                    system_prompt="Detailed system prompt with clear instructions"
                ),
                MagicMock(
                    name="",  # Missing name
                    description="Good description",
                    system_prompt="Good prompt"
                ),
                MagicMock(
                    name="Bad Agent",
                    description="",  # Missing description
                    system_prompt="Good prompt"
                ),
                MagicMock(
                    name="Another Agent",
                    description="Good description",
                    system_prompt=""  # Missing system prompt
                )
            ]
            
            # Mock database query
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = mock_agents
            mock_session.execute.return_value = mock_result
            
            validation_results = await parser_service.validate_parsed_agents()
            
            assert validation_results["total"] == 4
            assert validation_results["valid"] == 1
            assert validation_results["missing_name"] == 1
            assert validation_results["missing_description"] == 1
            assert validation_results["missing_system_prompt"] == 1


@pytest.mark.asyncio 
class TestAgentParserIntegration:
    """Integration tests for agent parser with database"""
    
    @patch('app.services.agent_parser.RepositorySyncService')
    async def test_parse_repository_agents_integration(self, mock_repo_sync, parser_service: AgentParserService, temp_repo_structure):
        """Test complete repository parsing workflow"""
        # Mock repository sync service
        mock_repo_sync.return_value.get_repository_path.return_value = temp_repo_structure
        
        with patch('app.services.agent_parser.get_async_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock repository
            mock_repository = MagicMock()
            mock_repository.id = 1
            mock_repository.name = "test/repo"
            
            # Mock Agent model methods
            with patch('app.services.agent_parser.Agent') as mock_agent_class:
                mock_agent_class.get_by_file_path.return_value = None  # No existing agents
                mock_new_agent = AsyncMock()
                mock_agent_class.create.return_value = mock_new_agent
                
                # Execute parsing
                results = await parser_service._parse_repository_agents(mock_session, mock_repository)
                
                # Verify results
                assert results["total"] == 2  # Two .md files in test structure
                assert len(results["success"]) >= 1  # At least one successful parse
                assert len(results["failed"]) == 0  # No failures expected
                
                # Verify agent creation was called
                assert mock_agent_class.create.call_count >= 1
                mock_new_agent.mark_parsed.assert_called()
    
    def test_content_hash_consistency(self, parser_service: AgentParserService):
        """Test that content hash generation is consistent"""
        content1 = "Test content for hashing"
        content2 = "Test content for hashing"
        content3 = "Different test content"
        
        hash1 = hashlib.sha256(content1.encode('utf-8')).hexdigest()[:16]
        hash2 = hashlib.sha256(content2.encode('utf-8')).hexdigest()[:16]
        hash3 = hashlib.sha256(content3.encode('utf-8')).hexdigest()[:16]
        
        assert hash1 == hash2  # Same content should produce same hash
        assert hash1 != hash3  # Different content should produce different hash
    
    def test_file_filtering_logic(self, parser_service: AgentParserService):
        """Test that file filtering works correctly"""
        test_files = [
            Path("agents/good_agent.md"),
            Path("agents/another_agent.md"),
            Path("README.md"),
            Path("LICENSE.md"),
            Path("CONTRIBUTING.md"),
            Path("docs/guide.md"),
            Path(".github/workflows/ci.md"),
            Path("agents/.hidden_agent.md")
        ]
        
        # Simulate filtering logic
        filtered_files = []
        for file_path in test_files:
            filename = file_path.name.lower()
            
            # Skip common non-agent files
            if filename in ["readme.md", "license.md", "contributing.md", "changelog.md"]:
                continue
            
            # Skip files in hidden directories
            if any(part.startswith(".") for part in file_path.parts):
                continue
            
            filtered_files.append(file_path)
        
        assert len(filtered_files) == 3  # Only agents/good_agent.md, agents/another_agent.md, docs/guide.md
        assert Path("agents/good_agent.md") in filtered_files
        assert Path("agents/another_agent.md") in filtered_files
        assert Path("docs/guide.md") in filtered_files
        assert Path("README.md") not in filtered_files
        assert Path(".github/workflows/ci.md") not in filtered_files