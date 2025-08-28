# Discovery endpoints for the agents API

from fastapi import Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.discovery import AgentDiscoveryService, DiscoveryContext


# Add these endpoints to the existing agents.py router

@router.get("/recommendations")
async def get_personalized_recommendations(
    search: Optional[str] = Query(None),
    lifecycle: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    tech_interests: Optional[List[str]] = Query(None),
    experience_level: str = Query("intermediate"),
    project_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20)
):
    """Get personalized agent recommendations"""
    discovery_service = AgentDiscoveryService()
    
    context = DiscoveryContext(
        search_query=search,
        preferred_lifecycle=lifecycle,
        preferred_role=role,
        tech_interests=tech_interests or [],
        experience_level=experience_level,
        project_type=project_type
    )
    
    recommendations = await discovery_service.get_personalized_recommendations(context, limit)
    
    return {
        "recommendations": [
            {
                "agent": {
                    "id": rec.agent.id,
                    "name": rec.agent.name,
                    "description": rec.agent.description,
                    "repository": rec.agent.repository.to_dict() if rec.agent.repository else {},
                    "classifications": rec.agent.primary_classification.to_dict() if rec.agent.primary_classification else {},
                    "tech_stack": rec.agent.tech_tags
                },
                "score": rec.score,
                "reasoning": rec.reasoning,
                "match_factors": rec.match_factors
            }
            for rec in recommendations
        ],
        "context": {
            "search_query": context.search_query,
            "preferred_lifecycle": context.preferred_lifecycle,
            "preferred_role": context.preferred_role,
            "tech_interests": context.tech_interests,
            "experience_level": context.experience_level
        }
    }


@router.get("/{agent_id}/similar")
async def get_similar_agents_enhanced(agent_id: int, limit: int = Query(6, ge=1, le=20)):
    """Get enhanced similar agents with detailed similarity analysis"""
    discovery_service = AgentDiscoveryService()
    similar_agents = await discovery_service.get_similar_agents(agent_id, limit)
    
    return {
        "similar_agents": similar_agents,
        "agent_id": agent_id
    }


@router.post("/complementary")
async def get_complementary_agents(
    agent_ids: List[int],
    limit: int = Query(5, ge=1, le=10)
):
    """Get agents that complement the selected ones"""
    discovery_service = AgentDiscoveryService()
    complementary = await discovery_service.get_complementary_agents(agent_ids, limit)
    
    return {
        "complementary_agents": complementary,
        "selected_agent_ids": agent_ids
    }


@router.get("/trending")
async def get_trending_agents(limit: int = Query(10, ge=1, le=20)):
    """Get currently trending agents"""
    discovery_service = AgentDiscoveryService()
    trending = await discovery_service.get_trending_agents(limit)
    
    return {
        "trending_agents": trending,
        "period": "last_7_days"
    }