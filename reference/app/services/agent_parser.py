# Agent parser service

import hashlib
import frontmatter
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.core.database import get_async_session
from app.models.repository import Repository
from app.models.agent import Agent
from app.services.repository_sync import RepositorySyncService


@dataclass
class ParsedAgent:
    """Parsed agent data structure"""
    name: str
    description: str
    file_path: str
    repository_id: int
    system_prompt: str
    yaml_metadata: Dict[str, Any]
    content_hash: str
    raw_content: str


class AgentParserService:
    """Service for parsing Claude Code subagents from markdown files"""
    
    def __init__(self):
        self.repo_sync = RepositorySyncService()
        self.supported_extensions = [".md", ".markdown"]
    
    async def parse_all_agents(self) -> Dict[str, Any]:
        """Parse all agents from all active repositories"""
        results = {
            "success": [],
            "failed": [],
            "skipped": [],
            "total": 0
        }
        
        async with get_async_session() as session:
            # Get all active repositories
            repositories = await Repository.get_all_active(session)
            
            for repository in repositories:
                repo_results = await self._parse_repository_agents(session, repository)
                
                results["success"].extend(repo_results["success"])
                results["failed"].extend(repo_results["failed"])
                results["skipped"].extend(repo_results["skipped"])
                results["total"] += repo_results["total"]
        
        return results
    
    async def parse_repository_agents(self, repository_name: str) -> Dict[str, Any]:
        """Parse agents from a specific repository"""
        async with get_async_session() as session:
            repository = await Repository.get_by_name(session, repository_name)
            if not repository:
                raise ValueError(f"Repository {repository_name} not found")
            
            return await self._parse_repository_agents(session, repository)
    
    async def _parse_repository_agents(self, session, repository: Repository) -> Dict[str, Any]:
        """Parse agents from a repository"""
        results = {
            "success": [],
            "failed": [],
            "skipped": [],
            "total": 0
        }
        
        try:
            # Get repository files
            repo_path = self.repo_sync.get_repository_path(repository.name)
            files = await self._get_agent_files(repo_path)
            results["total"] = len(files)
            
            print(f"Found {len(files)} potential agent files in {repository.name}")
            
            for file_path in files:
                try:
                    relative_path = str(file_path.relative_to(repo_path))
                    
                    # Check if agent already exists and is up to date
                    existing_agent = await Agent.get_by_file_path(session, relative_path, repository.id)
                    
                    # Parse the file
                    parsed_agent = await self._parse_agent_file(file_path, relative_path, repository.id)
                    
                    if existing_agent:
                        # Check if content has changed
                        if existing_agent.content_hash == parsed_agent.content_hash:
                            results["skipped"].append(relative_path)
                            continue
                        
                        # Update existing agent
                        await self._update_existing_agent(session, existing_agent, parsed_agent)
                    else:
                        # Create new agent
                        await self._create_new_agent(session, parsed_agent)
                    
                    results["success"].append(relative_path)
                    
                except Exception as e:
                    print(f"Failed to parse {file_path}: {str(e)}")
                    results["failed"].append({
                        "file": str(file_path),
                        "error": str(e)
                    })
        
        except Exception as e:
            print(f"Failed to parse repository {repository.name}: {str(e)}")
            results["failed"].append({
                "repository": repository.name,
                "error": str(e)
            })
        
        return results
    
    async def _get_agent_files(self, repo_path: Path) -> List[Path]:
        """Get all potential agent files from repository"""
        files = []
        
        for ext in self.supported_extensions:
            files.extend(repo_path.rglob(f"*{ext}"))
        
        # Filter out common non-agent files
        filtered_files = []
        for file_path in files:
            filename = file_path.name.lower()
            
            # Skip common documentation files
            if filename in ["readme.md", "license.md", "contributing.md", "changelog.md"]:
                continue
            
            # Skip files in certain directories
            if any(part.startswith(".") for part in file_path.parts):
                continue
            
            filtered_files.append(file_path)
        
        return filtered_files
    
    async def _parse_agent_file(self, file_path: Path, relative_path: str, repository_id: int) -> ParsedAgent:
        """Parse a single agent file"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # Calculate content hash
            content_hash = hashlib.sha256(raw_content.encode('utf-8')).hexdigest()[:16]
            
            # Try to parse frontmatter with enhanced error handling
            yaml_metadata = {}
            content = raw_content
            
            try:
                # Parse frontmatter normally
                post = frontmatter.loads(raw_content)
                yaml_metadata = post.metadata
                content = post.content
            except yaml.YAMLError as yaml_error:
                print(f"YAML parsing failed for {file_path}, attempting fallback parsing: {yaml_error}")
                # Fallback: try to extract basic metadata manually
                yaml_metadata, content = self._parse_problematic_frontmatter(raw_content)
            except Exception as parse_error:
                print(f"Frontmatter parsing failed for {file_path}, using content only: {parse_error}")
                # No frontmatter, use entire content
                yaml_metadata = {}
                content = raw_content
            
            # Extract agent information
            name = self._extract_name(yaml_metadata, file_path)
            description = self._extract_description(yaml_metadata, content)
            system_prompt = self._extract_system_prompt(content, yaml_metadata)
            
            return ParsedAgent(
                name=name,
                description=description,
                file_path=relative_path,
                repository_id=repository_id,
                system_prompt=system_prompt,
                yaml_metadata=yaml_metadata,
                content_hash=content_hash,
                raw_content=raw_content
            )
        
        except Exception as e:
            raise Exception(f"Failed to parse {file_path}: {str(e)}")
    
    def _extract_name(self, metadata: Dict[str, Any], file_path: Path) -> str:
        """Extract agent name from metadata or filename"""
        # Try various metadata fields
        name = metadata.get("name") or metadata.get("title") or metadata.get("agent_name")
        
        if name:
            return str(name).strip()
        
        # Fallback to filename
        return file_path.stem.replace("_", " ").replace("-", " ").title()
    
    def _extract_description(self, metadata: Dict[str, Any], content: str) -> str:
        """Extract agent description"""
        # Try metadata first
        description = metadata.get("description") or metadata.get("summary")
        
        if description:
            return str(description).strip()
        
        # Extract from content - look for first paragraph
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                return line[:200] + "..." if len(line) > 200 else line
        
        return "Claude Code subagent"
    
    def _extract_system_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        """Extract system prompt from content"""
        # Try metadata first
        system_prompt = metadata.get("system_prompt") or metadata.get("prompt")
        
        if system_prompt:
            return str(system_prompt).strip()
        
        # Extract from content
        # Look for code blocks or the main content
        lines = content.strip().split('\n')
        in_code_block = False
        code_content = []
        
        for line in lines:
            if line.strip().startswith('```'):
                if in_code_block:
                    break
                else:
                    in_code_block = True
                    continue
            
            if in_code_block:
                code_content.append(line)
        
        if code_content:
            return '\n'.join(code_content).strip()
        
        # Fallback to entire content
        return content.strip()
    
    async def _create_new_agent(self, session, parsed_agent: ParsedAgent):
        """Create a new agent in the database"""
        agent = await Agent.create(
            session,
            name=parsed_agent.name,
            description=parsed_agent.description,
            file_path=parsed_agent.file_path,
            repository_id=parsed_agent.repository_id,
            system_prompt=parsed_agent.system_prompt,
            yaml_metadata=parsed_agent.yaml_metadata
        )
        
        await agent.mark_parsed(session, parsed_agent.content_hash)
        return agent
    
    async def _update_existing_agent(self, session, existing_agent: Agent, parsed_agent: ParsedAgent):
        """Update an existing agent with new content"""
        existing_agent.name = parsed_agent.name
        existing_agent.description = parsed_agent.description
        existing_agent.system_prompt = parsed_agent.system_prompt
        existing_agent.yaml_metadata = parsed_agent.yaml_metadata
        existing_agent.is_classified = False  # Reclassify if content changed
        
        await existing_agent.mark_parsed(session, parsed_agent.content_hash)
        return existing_agent
    
    def _parse_problematic_frontmatter(self, raw_content: str) -> Tuple[Dict[str, Any], str]:
        """Fallback parser for YAML frontmatter that failed to parse properly"""
        metadata = {}
        content = raw_content
        
        # Check if content has frontmatter delimiters
        if not raw_content.strip().startswith('---'):
            return metadata, content
        
        try:
            # Split by frontmatter delimiters
            parts = raw_content.split('---', 2)
            if len(parts) < 3:
                return metadata, content
            
            # Extract the frontmatter section
            frontmatter_section = parts[1].strip()
            content = parts[2].strip()
            
            # Try to parse line by line, being more lenient
            for line in frontmatter_section.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Look for key: value patterns
                if ':' in line:
                    # Split only on first colon to handle values with colons
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Handle different value types
                    if value.startswith('"') and value.endswith('"'):
                        # Remove quotes but keep the content as-is
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        # Remove single quotes
                        value = value[1:-1]
                    elif value.lower() in ['true', 'false']:
                        # Boolean values
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        # Integer values
                        value = int(value)
                    # For complex values (like the long descriptions), keep as string
                    
                    metadata[key] = value
            
            print(f"Fallback parsing extracted {len(metadata)} metadata fields")
            return metadata, content
            
        except Exception as e:
            print(f"Fallback parsing also failed: {e}")
            # Return empty metadata and full content as fallback
            return {}, raw_content
    
    def _is_likely_agent_file(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Heuristic to determine if file contains a Claude Code subagent"""
        # Check for agent-specific keywords
        agent_keywords = [
            "system prompt", "agent", "claude", "assistant", "role", "behavior",
            "instructions", "task", "objective", "goal"
        ]
        
        content_lower = content.lower()
        metadata_str = str(metadata).lower()
        
        # Count keyword matches
        keyword_count = sum(1 for keyword in agent_keywords 
                          if keyword in content_lower or keyword in metadata_str)
        
        # Check for code blocks (common in agent definitions)
        has_code_blocks = "```" in content
        
        # Check for YAML frontmatter with agent-like structure
        has_agent_metadata = any(key in metadata for key in ["name", "description", "system_prompt", "role"])
        
        # Score the likelihood
        score = keyword_count * 10
        if has_code_blocks:
            score += 20
        if has_agent_metadata:
            score += 30
        
        return score >= 20
    
    async def validate_parsed_agents(self) -> Dict[str, Any]:
        """Validate parsed agents for completeness and quality"""
        validation_results = {
            "total": 0,
            "valid": 0,
            "missing_name": 0,
            "missing_description": 0,
            "missing_system_prompt": 0,
            "empty_content": 0
        }
        
        async with get_async_session() as session:
            stmt = select(Agent).where(Agent.is_parsed == True)
            result = await session.execute(stmt)
            agents = result.scalars().all()
            
            validation_results["total"] = len(agents)
            
            for agent in agents:
                is_valid = True
                
                if not agent.name or len(agent.name.strip()) < 2:
                    validation_results["missing_name"] += 1
                    is_valid = False
                
                if not agent.description or len(agent.description.strip()) < 10:
                    validation_results["missing_description"] += 1
                    is_valid = False
                
                if not agent.system_prompt or len(agent.system_prompt.strip()) < 20:
                    validation_results["missing_system_prompt"] += 1
                    is_valid = False
                
                if len(agent.system_prompt or "") < 10:
                    validation_results["empty_content"] += 1
                    is_valid = False
                
                if is_valid:
                    validation_results["valid"] += 1
        
        return validation_results