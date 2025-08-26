# Web pages router

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional, List
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.models.agent import Agent
from app.models.repository import Repository
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from config.settings import TEMPLATES_DIR, LIFECYCLE_PHASES, ROLE_TYPES

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage with two-row layout and featured agents"""
    async with get_async_session() as session:
        # Get repository statistics
        repositories = await Repository.get_all_active(session)
        total_agents = await Agent.count(session)
        classified_agents = await Agent.count_classified(session)
        
        # Get classification distribution
        try:
            distribution_stats = await Classification.get_distribution_stats(session)
        except:
            # Fallback if there are no classifications yet
            distribution_stats = {
                "lifecycle_phases": {},
                "role_types": {}
            }
        
        # Get featured agents (limit to avoid overwhelming display) with proper loading
        try:
            featured_agents_list = await Agent.get_popular(session, limit=6)
            # Format for template - simple list without accessing relationships
            featured_agents = {"popular": featured_agents_list}
        except:
            featured_agents = {"popular": []}
        
        return templates.TemplateResponse("pages/homepage.html", {
            "request": request,
            "featured_agents": featured_agents,
            "stats": {
                "total_repositories": len(repositories),
                "total_agents": total_agents,
                "classified_agents": classified_agents,
                "classification_rate": round((classified_agents / total_agents * 100) if total_agents > 0 else 0, 1)
            },
            "distribution_stats": distribution_stats,
            "lifecycle_phases": LIFECYCLE_PHASES,
            "role_types": ROLE_TYPES
        })


async def _count_filtered_agents(
    session,
    search: Optional[str] = None,
    lifecycle_phase: Optional[str] = None,
    role_type: Optional[str] = None,
    tech_stack: Optional[List[str]] = None,
    repository_id: Optional[int] = None
) -> int:
    """Count agents with the same filters as search_and_filter"""
    # Start with base count query
    count_stmt = select(func.count(Agent.id)).where(Agent.is_classified == True)
    
    # Apply same filters as in Agent.search_and_filter
    conditions = [Agent.is_classified == True]
    
    if search:
        conditions.append(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%"),
                Agent.system_prompt.ilike(f"%{search}%")
            )
        )
    
    if repository_id:
        conditions.append(Agent.repository_id == repository_id)
    
    # Handle classification filters - only join once even if both filters are present
    classification_joins_needed = bool(lifecycle_phase or role_type)
    if classification_joins_needed:
        count_stmt = count_stmt.join(Classification)
        if lifecycle_phase:
            conditions.append(Classification.lifecycle_phase == lifecycle_phase)
        if role_type:
            conditions.append(Classification.role_type == role_type)
    
    # Handle tech stack filter
    if tech_stack:
        count_stmt = count_stmt.join(TechStack)
        conditions.append(TechStack.tag.in_(tech_stack))
    
    # Apply all conditions
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    
    result = await session.execute(count_stmt)
    return result.scalar() or 0


@router.get("/agents", response_class=HTMLResponse)
async def agents_page(
    request: Request,
    search: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    tech_stack: Optional[List[str]] = Query(None),
    repository_id: Optional[str] = Query(None),  # Change to str to handle empty strings
    sort: str = Query("popularity"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100)
):
    """Agents listing page with search and filters"""
    offset = (page - 1) * limit
    
    # Convert repository_id to int if not empty
    repo_id = None
    if repository_id and repository_id.strip():
        try:
            repo_id = int(repository_id)
        except ValueError:
            repo_id = None
    
    async with get_async_session() as session:
        try:
            # Use the proper search_and_filter method from Agent model
            agents = await Agent.search_and_filter(
                session=session,
                search=search,
                lifecycle_phase=lifecycle,
                role_type=role,
                tech_stack=tech_stack,
                repository_id=repo_id,
                limit=limit,
                offset=offset
            )
            
            # Get total count for pagination with same filters as the search
            total_agents = await _count_filtered_agents(
                session=session,
                search=search,
                lifecycle_phase=lifecycle,
                role_type=role,
                tech_stack=tech_stack,
                repository_id=repo_id
            )
            total_pages = (total_agents + limit - 1) // limit if total_agents > 0 else 1
            
            # Get filter options
            repositories = await Repository.get_all_active(session)
            
        except Exception as e:
            # Fallback to empty results if there are any query issues
            print(f"Error in agents query: {e}")
            import traceback
            traceback.print_exc()
            agents = []
            total_agents = 0
            total_pages = 1
            repositories = []
        
        return templates.TemplateResponse("pages/agents.html", {
            "request": request,
            "agents": agents,
            "total": total_agents,  # Add total for the partial template
            "search": search,
            "filters": {
                "lifecycle": lifecycle,
                "role": role,
                "tech_stack": tech_stack,
                "repository_id": repo_id
            },
            "sort": sort,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_agents,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages
            },
            "filter_options": {
                "lifecycle_phases": LIFECYCLE_PHASES,
                "role_types": ROLE_TYPES,
                "repositories": repositories,
                "tech_categories": [],
                "popular_tech_tags": []
            }
        })


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail_page(request: Request, agent_id: int):
    """Agent detail page"""
    async with get_async_session() as session:
        agent = await Agent.get_by_id(session, agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get related agents
        related_agent_ids = await TechStack.get_related_agents(
            session, 
            agent.tech_tags, 
            exclude_agent_id=agent_id,
            limit=6
        )
        
        related_agents = []
        for related_id in related_agent_ids:
            related_agent = await Agent.get_by_id(session, related_id)
            if related_agent:
                related_agents.append(related_agent)
        
        return templates.TemplateResponse("pages/agent_detail.html", {
            "request": request,
            "agent": agent,
            "related_agents": related_agents,
            "primary_classification": agent.primary_classification
        })


@router.get("/compare", response_class=HTMLResponse)
async def comparison_page(
    request: Request,
    agent_ids: Optional[str] = Query(None)
):
    """Agent comparison page"""
    async with get_async_session() as session:
        compared_agents = []
        
        # Parse agent_ids from comma-separated string
        parsed_agent_ids = []
        if agent_ids:
            try:
                parsed_agent_ids = [int(id.strip()) for id in agent_ids.split(',') if id.strip()]
            except ValueError:
                # If parsing fails, ignore invalid IDs
                parsed_agent_ids = []
        
        if parsed_agent_ids:
            for agent_id in parsed_agent_ids[:10]:  # Limit to 10 agents max
                agent = await Agent.get_by_id(session, agent_id)
                if agent:
                    compared_agents.append(agent)
        
        # Convert agents to dictionaries for JSON serialization
        compared_agents_dict = []
        for agent in compared_agents:
            agent_dict = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "system_prompt": agent.system_prompt,
                "tech_tags": agent.tech_tags,
                "file_path": agent.file_path,
                "repository": agent.repository.to_dict() if agent.repository else None,
                "primary_classification": agent.primary_classification.to_dict() if agent.primary_classification else None
            }
            compared_agents_dict.append(agent_dict)
        
        return templates.TemplateResponse("pages/comparison.html", {
            "request": request,
            "compared_agents": compared_agents,
            "compared_agents_json": compared_agents_dict,
            "max_agents": 10
        })


@router.get("/download", response_class=HTMLResponse)
async def download_page(request: Request):
    """Download selection page"""
    async with get_async_session() as session:
        # Get popular agents for suggestions
        popular_agents = await Agent.get_popular(session, limit=12)
        
        return templates.TemplateResponse("pages/download.html", {
            "request": request,
            "popular_agents": popular_agents,
            "max_agents_per_download": 50
        })


@router.get("/repositories", response_class=HTMLResponse)
async def repositories_page(request: Request):
    """Repositories page"""
    async with get_async_session() as session:
        repositories = await Repository.get_all_active(session)
        
        # Add agent counts for each repository using proper async queries
        for repo in repositories:
            # Count classified agents for this repository
            agent_count_stmt = select(func.count(Agent.id)).where(
                and_(Agent.repository_id == repo.id, Agent.is_classified == True)
            )
            result = await session.execute(agent_count_stmt)
            repo.agent_count = result.scalar() or 0
        
        return templates.TemplateResponse("pages/repositories.html", {
            "request": request,
            "repositories": repositories
        })


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page"""
    return templates.TemplateResponse("pages/about.html", {
        "request": request
    })


# HTMX partial endpoints for dynamic content
@router.get("/partials/agent-cards")
async def agent_cards_partial(
    request: Request,
    search: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    tech_stack: Optional[List[str]] = Query(None),
    repository_id: Optional[str] = Query(None),  # Change to str to handle empty strings
    sort: str = Query("popularity"),
    page: int = Query(1),
    limit: int = Query(12)
):
    """Return agent cards partial for HTMX updates"""
    offset = (page - 1) * limit
    
    # Convert repository_id to int if not empty
    repo_id = None
    if repository_id and repository_id.strip():
        try:
            repo_id = int(repository_id)
        except ValueError:
            repo_id = None
    
    async with get_async_session() as session:
        agents = await Agent.search_and_filter(
            session,
            search=search,
            lifecycle_phase=lifecycle,
            role_type=role,
            tech_stack=tech_stack,
            repository_id=repo_id,
            limit=limit,
            offset=offset
        )
        
        # Use filtered count for accurate pagination
        total_agents = await _count_filtered_agents(
            session=session,
            search=search,
            lifecycle_phase=lifecycle,
            role_type=role,
            tech_stack=tech_stack,
            repository_id=repo_id
        )
        
        # Calculate pagination data
        total_pages = (total_agents + limit - 1) // limit if total_agents > 0 else 1
        
        return templates.TemplateResponse("partials/agent_results_with_count.html", {
            "request": request,
            "agents": agents,
            "total": total_agents,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_agents,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages
            },
            # Include current filters for pagination links
            "filters": {
                "search": search,
                "lifecycle": lifecycle,
                "role": role,
                "tech_stack": tech_stack,
                "repository_id": repository_id,
                "sort": sort
            }
        })


@router.get("/partials/selection-summary")
async def selection_summary_partial(request: Request, session_id: str):
    """Return selection summary partial for HTMX updates"""
    async with get_async_session() as session:
        from app.models.download_selection import DownloadSelection
        
        selections = await DownloadSelection.get_session_selections(session, session_id)
        
        selected_agents = []
        for selection in selections:
            agent = await Agent.get_by_id(session, selection.agent_id)
            if agent:
                selected_agents.append(agent)
        
        return templates.TemplateResponse("partials/selection_summary.html", {
            "request": request,
            "selected_agents": selected_agents,
            "selection_count": len(selected_agents)
        })


async def _get_featured_agents(session) -> dict:
    """Get featured agents for homepage showcase"""
    featured = {}
    
    # Get agents from different categories
    categories = [
        ("architects", "system-architect"),
        ("developers", "backend-developer"),
        ("optimizers", "performance-engineer"),
        ("testers", "qa-tester")
    ]
    
    for category_name, role_type in categories:
        agents = await Agent.search_and_filter(
            session,
            role_type=role_type,
            limit=3
        )
        featured[category_name] = agents
    
    return featured