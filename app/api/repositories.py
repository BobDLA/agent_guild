# Repositories API endpoints

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from pydantic import BaseModel

from app.core.database import get_async_session
from app.models.repository import Repository
from app.services.repository_sync import RepositorySyncService
from app.services.agent_parser import AgentParserService
from app.services.classification import ClassificationService

router = APIRouter()


# Response models
class RepositoryInfo(BaseModel):
    """Repository information"""
    id: int
    name: str
    url: str
    description: str
    star_count: int
    fork_count: int
    language: Optional[str] = None
    license: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    last_synced_at: Optional[str] = None


class RepositoryStats(BaseModel):
    """Repository statistics"""
    total_repositories: int
    active_repositories: int
    total_agents: int
    last_sync_summary: dict


class SyncResponse(BaseModel):
    """Synchronization response"""
    status: str
    message: str
    task_id: Optional[str] = None


@router.get("/", response_model=List[RepositoryInfo])
async def list_repositories():
    """List all configured repositories with metadata"""
    async with get_async_session() as session:
        repositories = await Repository.get_all_active(session)
        
        repo_infos = []
        for repo in repositories:
            repo_info = RepositoryInfo(
                id=repo.id,
                name=repo.name,
                url=repo.url,
                description=repo.description or "",
                star_count=repo.star_count or 0,
                fork_count=repo.fork_count or 0,
                language=repo.language,
                license=repo.license,
                is_active=repo.is_active,
                created_at=repo.created_at.isoformat() if repo.created_at else "",
                updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
                last_synced_at=repo.last_synced_at.isoformat() if repo.last_synced_at else None
            )
            repo_infos.append(repo_info)
        
        return repo_infos


@router.get("/stats", response_model=RepositoryStats)
async def get_repository_stats():
    """Get repository and agent statistics"""
    async with get_async_session() as session:
        from app.models.agent import Agent
        
        # Repository stats
        total_repos = await Repository.count(session)
        active_repos = len(await Repository.get_all_active(session))
        
        # Agent stats
        total_agents = await Agent.count(session)
        
        # Last sync summary (placeholder)
        last_sync_summary = {
            "last_sync_time": "Not available",
            "repositories_synced": active_repos,
            "agents_processed": total_agents,
            "status": "healthy"
        }
        
        return RepositoryStats(
            total_repositories=total_repos,
            active_repositories=active_repos,
            total_agents=total_agents,
            last_sync_summary=last_sync_summary
        )


@router.post("/sync", response_model=SyncResponse)
async def trigger_full_sync(background_tasks: BackgroundTasks):
    """Trigger full repository synchronization (admin endpoint)"""
    # Add background task for full sync
    background_tasks.add_task(run_full_sync_pipeline)
    
    return SyncResponse(
        status="started",
        message="Full synchronization pipeline started in background",
        task_id="full_sync_" + str(int(time.time()))
    )


@router.post("/sync/{repository_name}", response_model=SyncResponse) 
async def trigger_repository_sync(repository_name: str, background_tasks: BackgroundTasks):
    """Trigger synchronization for a specific repository"""
    # Validate repository exists in configuration
    from config.settings import CONFIGURED_REPOSITORIES
    
    repo_config = None
    for config in CONFIGURED_REPOSITORIES:
        if config["name"] == repository_name:
            repo_config = config
            break
    
    if not repo_config:
        raise HTTPException(
            status_code=404, 
            detail=f"Repository {repository_name} not found in configuration"
        )
    
    # Add background task for single repository sync
    background_tasks.add_task(run_single_repository_sync, repository_name)
    
    return SyncResponse(
        status="started",
        message=f"Synchronization started for repository {repository_name}",
        task_id=f"sync_{repository_name}_{int(time.time())}"
    )


@router.get("/{repository_id}/agents")
async def get_repository_agents(repository_id: int, limit: int = 50, offset: int = 0):
    """Get agents from a specific repository"""
    async with get_async_session() as session:
        from app.models.agent import Agent
        
        # Verify repository exists
        repository = await Repository.get_by_id(session, repository_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Get agents for this repository
        agents = await Agent.search_and_filter(
            session,
            repository_id=repository_id,
            limit=limit,
            offset=offset
        )
        
        agent_summaries = []
        for agent in agents:
            primary_classification = agent.primary_classification
            
            agent_summaries.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "file_path": agent.file_path,
                "classifications": primary_classification.to_dict() if primary_classification else None,
                "tech_stack": agent.tech_tags,
                "created_at": agent.created_at.isoformat() if agent.created_at else ""
            })
        
        return {
            "repository": repository.to_dict(),
            "agents": agent_summaries,
            "total": len(agent_summaries),
            "page": (offset // limit) + 1,
            "limit": limit
        }


@router.delete("/{repository_id}")
async def deactivate_repository(repository_id: int):
    """Deactivate a repository (admin endpoint)"""
    async with get_async_session() as session:
        repository = await Repository.get_by_id(session, repository_id)
        
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        repository.is_active = False
        await session.flush()
        
        return {"message": f"Repository {repository.name} deactivated"}


# Background task functions
async def run_full_sync_pipeline():
    """Run the complete synchronization pipeline"""
    try:
        print("Starting full synchronization pipeline...")
        
        # Step 1: Sync repositories
        sync_service = RepositorySyncService()
        sync_results = await sync_service.sync_all_repositories()
        print(f"Repository sync completed: {sync_results}")
        
        # Step 2: Parse agents
        parser_service = AgentParserService()
        parse_results = await parser_service.parse_all_agents()
        print(f"Agent parsing completed: {parse_results}")
        
        # Step 3: Classify agents
        classification_service = ClassificationService()
        classify_results = await classification_service.classify_all_agents()
        print(f"Agent classification completed: {classify_results}")
        
        print("Full synchronization pipeline completed successfully!")
        
    except Exception as e:
        print(f"Full synchronization pipeline failed: {str(e)}")


async def run_single_repository_sync(repository_name: str):
    """Run synchronization for a single repository"""
    try:
        print(f"Starting synchronization for repository: {repository_name}")
        
        # Sync repository
        sync_service = RepositorySyncService()
        await sync_service.sync_repository(repository_name)
        
        # Parse agents for this repository
        parser_service = AgentParserService()
        parse_results = await parser_service.parse_repository_agents(repository_name)
        print(f"Agent parsing for {repository_name}: {parse_results}")
        
        # Classify new agents
        classification_service = ClassificationService()
        classify_results = await classification_service.classify_all_agents()
        print(f"Classification results: {classify_results}")
        
        print(f"Synchronization completed for repository: {repository_name}")
        
    except Exception as e:
        print(f"Repository synchronization failed for {repository_name}: {str(e)}")


import time