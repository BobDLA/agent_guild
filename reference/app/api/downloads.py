# Downloads API endpoints

import os
import zipfile
import tempfile
import io
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_async_session
from app.models.agent import Agent
from app.models.download_selection import DownloadSelection
from config.settings import MAX_AGENTS_PER_DOWNLOAD

router = APIRouter()


# Request models
class AddToSelectionRequest(BaseModel):
    """Add agent to download selection"""
    session_id: str = Field(..., min_length=1, max_length=255)
    agent_id: int


class RemoveFromSelectionRequest(BaseModel):
    """Remove agent from download selection"""
    session_id: str = Field(..., min_length=1, max_length=255)
    agent_id: int


class GeneratePackageRequest(BaseModel):
    """Generate download package"""
    session_id: str = Field(..., min_length=1, max_length=255)
    include_readme: bool = True
    package_name: Optional[str] = Field(None, max_length=100)


class BulkDownloadRequest(BaseModel):
    """Bulk download request"""
    agent_ids: List[int] = Field(..., min_items=1, max_items=MAX_AGENTS_PER_DOWNLOAD)
    include_readme: bool = True
    package_name: Optional[str] = Field(None, max_length=100)


# Response models
class SelectionResponse(BaseModel):
    """Selection operation response"""
    status: str
    message: str
    selection_count: int


class DownloadStatsResponse(BaseModel):
    """Download statistics"""
    popular_agents: List[dict]
    recent_downloads: int
    total_packages_generated: int


@router.post("/selection/add", response_model=SelectionResponse)
async def add_to_selection(request: AddToSelectionRequest):
    """Add an agent to download selection"""
    async with get_async_session() as session:
        # Verify agent exists
        agent = await Agent.get_by_id(session, request.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Check selection limit
        current_selections = await DownloadSelection.get_session_selections(session, request.session_id)
        if len(current_selections) >= MAX_AGENTS_PER_DOWNLOAD:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_AGENTS_PER_DOWNLOAD} agents allowed per download"
            )
        
        # Add to selection
        await DownloadSelection.add_to_selection(session, request.session_id, request.agent_id)
        
        # Get updated count
        updated_selections = await DownloadSelection.get_session_selections(session, request.session_id)
        
        return SelectionResponse(
            status="success",
            message=f"Agent '{agent.name}' added to selection",
            selection_count=len(updated_selections)
        )


@router.post("/selection/remove", response_model=SelectionResponse)
async def remove_from_selection(request: RemoveFromSelectionRequest):
    """Remove an agent from download selection"""
    async with get_async_session() as session:
        # Remove from selection
        await DownloadSelection.remove_from_selection(session, request.session_id, request.agent_id)
        
        # Get updated count
        updated_selections = await DownloadSelection.get_session_selections(session, request.session_id)
        
        return SelectionResponse(
            status="success",
            message="Agent removed from selection",
            selection_count=len(updated_selections)
        )


@router.get("/selection/{session_id}")
async def get_selection(session_id: str):
    """Get current download selection for session"""
    async with get_async_session() as session:
        selections = await DownloadSelection.get_session_selections(session, session_id)
        
        selected_agents = []
        for selection in selections:
            agent = await Agent.get_by_id(session, selection.agent_id)
            if agent:
                primary_classification = agent.primary_classification
                
                selected_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "repository": agent.repository.to_dict() if agent.repository else {},
                    "classifications": primary_classification.to_dict() if primary_classification else None,
                    "tech_stack": agent.tech_tags,
                    "selected_at": selection.selected_at.isoformat()
                })
        
        return {
            "session_id": session_id,
            "selected_agents": selected_agents,
            "total_selected": len(selected_agents)
        }


@router.post("/selection/clear")
async def clear_selection(session_id: str):
    """Clear all selections for a session"""
    async with get_async_session() as session:
        await DownloadSelection.clear_session_selections(session, session_id)
        
        return SelectionResponse(
            status="success",
            message="Selection cleared",
            selection_count=0
        )


@router.post("/package/generate")
async def generate_package(request: GeneratePackageRequest):
    """Generate and download ZIP package of selected agents"""
    async with get_async_session() as session:
        # Get selected agents
        agent_ids = await DownloadSelection.get_session_agent_ids(session, request.session_id)
        
        if not agent_ids:
            raise HTTPException(status_code=400, detail="No agents selected for download")
        
        # Generate package
        zip_content = await _create_agent_package(
            session, 
            agent_ids, 
            request.include_readme,
            request.package_name or "subagent_guild_package"
        )
        
        # Create a BytesIO object to stream the content
        zip_io = io.BytesIO(zip_content)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(zip_content),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={request.package_name or 'subagent_guild_package'}.zip"
            }
        )


@router.post("/package/bulk")
async def bulk_download(request: BulkDownloadRequest):
    """Generate and download ZIP package for specified agents"""
    async with get_async_session() as session:
        # Validate all agents exist
        for agent_id in request.agent_ids:
            agent = await Agent.get_by_id(session, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Generate package
        zip_content = await _create_agent_package(
            session,
            request.agent_ids,
            request.include_readme,
            request.package_name or "subagent_guild_bulk"
        )
        
        return StreamingResponse(
            io.BytesIO(zip_content),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={request.package_name or 'subagent_guild_bulk'}.zip"
            }
        )


@router.get("/stats", response_model=DownloadStatsResponse)
async def get_download_stats():
    """Get download statistics"""
    async with get_async_session() as session:
        # Get popular agents by download count
        popular_agent_ids = await DownloadSelection.get_popular_agents(session, limit=10)
        
        popular_agents = []
        for agent_id in popular_agent_ids:
            agent = await Agent.get_by_id(session, agent_id)
            if agent:
                popular_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "repository": agent.repository.name if agent.repository else "Unknown"
                })
        
        # Get download statistics
        download_stats = await DownloadSelection.get_download_stats(session, days=30)
        
        return DownloadStatsResponse(
            popular_agents=popular_agents,
            recent_downloads=len(download_stats),
            total_packages_generated=sum(stat["download_count"] for stat in download_stats)
        )


async def _create_agent_package(
    session, 
    agent_ids: List[int], 
    include_readme: bool = True,
    package_name: str = "subagent_package"
) -> bytes:
    """Create ZIP package containing selected agents"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_path = temp_path / f"{package_name}.zip"
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            agents_added = []
            
            # Add each agent
            for agent_id in agent_ids:
                agent = await Agent.get_by_id(session, agent_id)
                if not agent:
                    continue
                
                # Create safe filename
                safe_name = _sanitize_filename(agent.name)
                agent_filename = f"agents/{safe_name}.md"
                
                # Create agent content
                agent_content = _create_agent_file_content(agent)
                
                # Add to ZIP
                zipf.writestr(agent_filename, agent_content)
                agents_added.append(agent)
            
            # Add README if requested
            if include_readme:
                readme_content = _create_package_readme(agents_added, package_name)
                zipf.writestr("README.md", readme_content)
            
            # Add metadata file
            metadata_content = _create_package_metadata(agents_added)
            zipf.writestr("package_metadata.json", metadata_content)
        
        # Read ZIP content
        with open(package_path, 'rb') as zipf:
            zip_content = zipf.read()
    
    return zip_content


def _create_agent_file_content(agent: Agent) -> str:
    """Create markdown content for an agent file"""
    content_parts = []
    
    # YAML frontmatter
    frontmatter = {
        "name": agent.name,
        "description": agent.description,
        "repository": agent.repository.name if agent.repository else "unknown",
        "file_path": agent.file_path
    }
    
    # Add classification info
    primary_classification = agent.primary_classification
    if primary_classification:
        frontmatter.update({
            "lifecycle_phase": primary_classification.lifecycle_phase,
            "role_type": primary_classification.role_type,
            "confidence_score": primary_classification.confidence_score
        })
    
    # Add tech stack
    if agent.tech_tags:
        frontmatter["tech_stack"] = agent.tech_tags
    
    # Add original metadata
    if agent.yaml_metadata:
        frontmatter.update(agent.yaml_metadata)
    
    # Create YAML frontmatter
    import yaml
    yaml_content = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    
    content_parts.append("---")
    content_parts.append(yaml_content.strip())
    content_parts.append("---")
    content_parts.append("")
    
    # Add description
    content_parts.append(f"# {agent.name}")
    content_parts.append("")
    content_parts.append(agent.description or "")
    content_parts.append("")
    
    # Add system prompt
    if agent.system_prompt:
        content_parts.append("## System Prompt")
        content_parts.append("")
        content_parts.append("```")
        content_parts.append(agent.system_prompt)
        content_parts.append("```")
    
    return "\n".join(content_parts)


def _create_package_readme(agents: List[Agent], package_name: str) -> str:
    """Create README for the package"""
    content_parts = []
    
    content_parts.append(f"# {package_name.replace('_', ' ').title()}")
    content_parts.append("")
    content_parts.append("This package contains Claude Code subagents from the Subagent Guild.")
    content_parts.append("")
    content_parts.append(f"**Package generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    content_parts.append(f"**Total agents:** {len(agents)}")
    content_parts.append("")
    
    # Table of contents
    content_parts.append("## Included Agents")
    content_parts.append("")
    content_parts.append("| Agent | Description | Repository | Role |")
    content_parts.append("|-------|-------------|------------|------|")
    
    for agent in agents:
        primary_classification = agent.primary_classification
        role = primary_classification.role_type if primary_classification else "general"
        repo_name = agent.repository.name if agent.repository else "unknown"
        
        content_parts.append(f"| {agent.name} | {agent.description[:50]}... | {repo_name} | {role} |")
    
    content_parts.append("")
    
    # Usage instructions
    content_parts.append("## Usage")
    content_parts.append("")
    content_parts.append("Each agent is provided as a markdown file with YAML frontmatter containing:")
    content_parts.append("- Agent metadata (name, description, classification)")
    content_parts.append("- System prompt for use with Claude")
    content_parts.append("- Technology stack information")
    content_parts.append("")
    content_parts.append("To use an agent:")
    content_parts.append("1. Open the desired agent's `.md` file")
    content_parts.append("2. Copy the system prompt content")
    content_parts.append("3. Use it as the system prompt in your Claude conversation")
    content_parts.append("")
    
    # Credits
    content_parts.append("## Credits")
    content_parts.append("")
    content_parts.append("These agents are sourced from public repositories and curated by the Subagent Guild.")
    content_parts.append("Original repository information is preserved in each agent's metadata.")
    content_parts.append("")
    
    return "\n".join(content_parts)


def _create_package_metadata(agents: List[Agent]) -> str:
    """Create metadata JSON for the package"""
    import json
    from datetime import datetime
    
    metadata = {
        "package_info": {
            "generated_at": datetime.utcnow().isoformat(),
            "total_agents": len(agents),
            "source": "Subagent Guild"
        },
        "agents": []
    }
    
    for agent in agents:
        primary_classification = agent.primary_classification
        
        agent_metadata = {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "file_path": f"agents/{_sanitize_filename(agent.name)}.md",
            "repository": {
                "name": agent.repository.name if agent.repository else "unknown",
                "url": agent.repository.url if agent.repository else ""
            },
            "classification": {
                "lifecycle_phase": primary_classification.lifecycle_phase if primary_classification else "general",
                "role_type": primary_classification.role_type if primary_classification else "general",
                "confidence_score": primary_classification.confidence_score if primary_classification else 0.5
            },
            "tech_stack": agent.tech_tags
        }
        
        metadata["agents"].append(agent_metadata)
    
    return json.dumps(metadata, indent=2, ensure_ascii=False)


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename for use in ZIP archive"""
    import re
    
    # Replace invalid characters
    sanitized = re.sub(r'[^\w\s-]', '', filename)
    
    # Replace spaces with underscores
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    
    return sanitized.strip('_').lower()


from datetime import datetime