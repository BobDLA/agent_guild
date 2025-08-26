# Agents API endpoints

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_async_session
from app.models.agent import Agent
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.services.classification import ClassificationService

router = APIRouter()


# Response models
class AgentSummary(BaseModel):
    """Agent summary for listings"""
    id: int
    name: str
    description: str
    repository: dict
    classifications: Optional[dict] = None
    tech_stack: List[str] = []
    

class AgentDetail(BaseModel):
    """Detailed agent information"""
    id: int
    name: str
    description: str
    file_path: str
    repository: dict
    system_prompt: str
    yaml_metadata: dict
    classifications: List[dict] = []
    tech_stack: List[str] = []
    created_at: str
    updated_at: Optional[str] = None


class AgentSearchResponse(BaseModel):
    """Agent search response"""
    agents: List[AgentSummary]
    total: int
    page: int
    limit: int
    has_next: bool


class RelatedAgentsResponse(BaseModel):
    """Related agents response"""
    related_agents: List[dict]


# Request models
class AgentCompareRequest(BaseModel):
    """Agent comparison request"""
    agent_ids: List[int] = Field(..., min_items=2, max_items=10)


@router.get("/", response_model=AgentSearchResponse)
async def search_agents(
    search: Optional[str] = Query(None, description="Search query"),
    lifecycle: Optional[str] = Query(None, description="Lifecycle phase filter"),
    role: Optional[str] = Query(None, description="Role type filter"),
    tech_stack: Optional[List[str]] = Query(None, description="Technology stack filter"),
    repository_id: Optional[int] = Query(None, description="Repository filter"),
    sort: str = Query("popularity", description="Sort order (popularity, name, recent)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Search and filter agents"""
    async with get_async_session() as session:
        # Perform search
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
        total = await Agent.count(session)
        
        # Convert to response format
        agent_summaries = []
        for agent in agents:
            primary_classification = agent.primary_classification
            
            agent_summary = AgentSummary(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                repository=agent.repository.to_dict() if agent.repository else {},
                classifications=primary_classification.to_dict() if primary_classification else None,
                tech_stack=agent.tech_tags
            )
            agent_summaries.append(agent_summary)
        
        return AgentSearchResponse(
            agents=agent_summaries,
            total=total,
            page=(offset // limit) + 1,
            limit=limit,
            has_next=offset + limit < total
        )


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(agent_id: int):
    """Get detailed agent information"""
    async with get_async_session() as session:
        agent = await Agent.get_by_id(session, agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return AgentDetail(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            file_path=agent.file_path,
            repository=agent.repository.to_dict() if agent.repository else {},
            system_prompt=agent.system_prompt or "",
            yaml_metadata=agent.yaml_metadata or {},
            classifications=[c.to_dict() for c in agent.classifications],
            tech_stack=agent.tech_tags,
            created_at=agent.created_at.isoformat() if agent.created_at else "",
            updated_at=agent.updated_at.isoformat() if agent.updated_at else None
        )


@router.get("/{agent_id}/related", response_model=RelatedAgentsResponse)
async def get_related_agents(agent_id: int, limit: int = Query(5, ge=1, le=20)):
    """Get agents related to the specified agent"""
    async with get_async_session() as session:
        agent = await Agent.get_by_id(session, agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Find related agents based on tech stack similarity
        related_agent_ids = await TechStack.get_related_agents(
            session, 
            agent.tech_tags, 
            exclude_agent_id=agent_id,
            limit=limit
        )
        
        related_agents = []
        for related_id in related_agent_ids:
            related_agent = await Agent.get_by_id(session, related_id)
            if related_agent:
                # Calculate similarity score based on shared tech tags
                shared_tags = set(agent.tech_tags) & set(related_agent.tech_tags)
                similarity_score = len(shared_tags) / max(len(agent.tech_tags), 1)
                
                related_agents.append({
                    "id": related_agent.id,
                    "name": related_agent.name,
                    "description": related_agent.description,
                    "relationship": "similar_tech_stack",
                    "similarity_score": similarity_score,
                    "shared_tags": list(shared_tags)
                })
        
        return RelatedAgentsResponse(related_agents=related_agents)


@router.get("/popular/trending")
async def get_popular_agents(limit: int = Query(10, ge=1, le=20)):
    """Get popular/trending agents"""
    async with get_async_session() as session:
        agents = await Agent.get_popular(session, limit=limit)
        
        agent_summaries = []
        for agent in agents:
            primary_classification = agent.primary_classification
            
            agent_summary = AgentSummary(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                repository=agent.repository.to_dict() if agent.repository else {},
                classifications=primary_classification.to_dict() if primary_classification else None,
                tech_stack=agent.tech_tags
            )
            agent_summaries.append(agent_summary)
        
        return {"popular_agents": agent_summaries}


@router.post("/compare")
async def compare_agents(request: AgentCompareRequest):
    """Compare multiple agents side-by-side"""
    async with get_async_session() as session:
        compared_agents = []
        
        for agent_id in request.agent_ids:
            agent = await Agent.get_by_id(session, agent_id)
            
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            
            primary_classification = agent.primary_classification
            
            compared_agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "repository": agent.repository.to_dict() if agent.repository else {},
                "system_prompt": agent.system_prompt or "",
                "yaml_metadata": agent.yaml_metadata or {},
                "classifications": primary_classification.to_dict() if primary_classification else None,
                "tech_stack": agent.tech_tags,
                "file_path": agent.file_path
            })
        
        # Generate comparison insights
        insights = await _generate_comparison_insights(compared_agents)
        
        return {
            "agents": compared_agents,
            "comparison_insights": insights
        }


@router.post("/{agent_id}/classify")
async def trigger_agent_classification(agent_id: int):
    """Trigger classification for a specific agent (admin endpoint)"""
    async with get_async_session() as session:
        agent = await Agent.get_by_id(session, agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        classification_service = ClassificationService()
        result = await classification_service.classify_single_agent(agent_id)
        
        return {
            "agent_id": agent_id,
            "classification": {
                "lifecycle_phase": result.lifecycle_phase,
                "role_type": result.role_type,
                "confidence_score": result.confidence_score,
                "tech_stack": result.tech_stack,
                "reasoning": result.reasoning
            }
        }


async def _generate_comparison_insights(agents: List[dict]) -> dict:
    """Generate insights for agent comparison"""
    if not agents:
        return {}
    
    # Analyze similarities and differences
    all_tech_stacks = [set(agent.get("tech_stack", [])) for agent in agents]
    shared_technologies = set.intersection(*all_tech_stacks) if all_tech_stacks else set()
    
    # Find unique technologies per agent
    unique_technologies = {}
    for i, agent in enumerate(agents):
        agent_tech = set(agent.get("tech_stack", []))
        other_tech = set.union(*(all_tech_stacks[:i] + all_tech_stacks[i+1:]))
        unique_technologies[agent["id"]] = list(agent_tech - other_tech)
    
    # Analyze complexity levels
    complexity_analysis = {}
    for agent in agents:
        prompt_length = len(agent.get("system_prompt", ""))
        metadata_complexity = len(agent.get("yaml_metadata", {}))
        
        if prompt_length > 1000 or metadata_complexity > 5:
            complexity = "advanced"
        elif prompt_length > 500 or metadata_complexity > 2:
            complexity = "intermediate"
        else:
            complexity = "beginner"
        
        complexity_analysis[agent["id"]] = complexity
    
    return {
        "shared_technologies": list(shared_technologies),
        "unique_technologies": unique_technologies,
        "complexity_levels": complexity_analysis,
        "recommendations": _generate_selection_recommendations(agents, shared_technologies)
    }


def _generate_selection_recommendations(agents: List[dict], shared_tech: set) -> List[str]:
    """Generate recommendations for agent selection"""
    recommendations = []
    
    if len(shared_tech) > 2:
        recommendations.append(f"These agents share {len(shared_tech)} technologies - they work well together")
    
    # Check for complementary roles
    roles = [agent.get("classifications", {}).get("role_type") for agent in agents if agent.get("classifications")]
    unique_roles = set(filter(None, roles))
    
    if len(unique_roles) == len(agents):
        recommendations.append("These agents have complementary roles - good for comprehensive coverage")
    
    # Check for lifecycle coverage
    phases = [agent.get("classifications", {}).get("lifecycle_phase") for agent in agents if agent.get("classifications")]
    unique_phases = set(filter(None, phases))
    
    if len(unique_phases) > 2:
        recommendations.append("These agents cover multiple development phases")
    
    return recommendations