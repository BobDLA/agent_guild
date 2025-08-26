# Web pages router

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional, List

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
        # Get featured agents for each category
        featured_agents = await _get_featured_agents(session)
        
        # Get repository statistics
        repositories = await Repository.get_all_active(session)
        total_agents = await Agent.count(session)
        classified_agents = await Agent.count_classified(session)
        
        # Get classification distribution
        distribution_stats = await Classification.get_distribution_stats(session)
        
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


@router.get("/agents", response_class=HTMLResponse)
async def agents_page(
    request: Request,
    search: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    tech_stack: Optional[List[str]] = Query(None),
    repository_id: Optional[int] = Query(None),
    sort: str = Query("popularity"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Agents listing page with search and filters"""
    offset = (page - 1) * limit
    
    async with get_async_session() as session:
        # Search agents
        agents = await Agent.search_and_filter(
            session,
            search=search,
            lifecycle_phase=lifecycle,
            role_type=role,
            tech_stack=tech_stack,
            repository_id=repository_id,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_agents = await Agent.count(session)
        total_pages = (total_agents + limit - 1) // limit
        
        # Get filter options
        repositories = await Repository.get_all_active(session)
        tech_categories = await TechStack.get_categories(session)
        popular_tech_tags = await TechStack.get_popular_tags(session, limit=20)
        
        return templates.TemplateResponse("pages/agents.html", {
            "request": request,
            "agents": agents,
            "search": search,
            "filters": {
                "lifecycle": lifecycle,
                "role": role,
                "tech_stack": tech_stack,
                "repository_id": repository_id
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
                "tech_categories": tech_categories,
                "popular_tech_tags": popular_tech_tags
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
    agent_ids: Optional[List[int]] = Query(None)
):
    """Agent comparison page"""
    async with get_async_session() as session:
        compared_agents = []
        
        if agent_ids:
            for agent_id in agent_ids[:10]:  # Limit to 10 agents max
                agent = await Agent.get_by_id(session, agent_id)
                if agent:
                    compared_agents.append(agent)
        
        return templates.TemplateResponse("pages/comparison.html", {
            "request": request,
            "compared_agents": compared_agents,
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
        
        # Add agent counts for each repository
        for repo in repositories:
            repo.agent_count = len([a for a in repo.agents if a.is_classified])
        
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
    sort: str = Query("popularity"),
    page: int = Query(1),
    limit: int = Query(20)
):
    """Return agent cards partial for HTMX updates"""
    offset = (page - 1) * limit
    
    async with get_async_session() as session:
        agents = await Agent.search_and_filter(
            session,
            search=search,
            lifecycle_phase=lifecycle,
            role_type=role,
            tech_stack=tech_stack,
            limit=limit,
            offset=offset
        )
        
        total_agents = await Agent.count(session)
        
        return templates.TemplateResponse("partials/agent_cards.html", {
            "request": request,
            "agents": agents,
            "page": page,
            "total": total_agents,
            "has_next": offset + limit < total_agents
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