# Enhanced Agent Discovery Service

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_async_session
from app.models.agent import Agent
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.models.repository import Repository
from app.models.download_selection import DownloadSelection


@dataclass
class DiscoveryContext:
    """User context for personalized discovery"""
    search_query: Optional[str] = None
    preferred_lifecycle: Optional[str] = None
    preferred_role: Optional[str] = None
    tech_interests: List[str] = None
    experience_level: str = "intermediate"  # beginner, intermediate, advanced
    project_type: Optional[str] = None  # web, mobile, api, data, etc.


@dataclass
class AgentRecommendation:
    """Agent recommendation with reasoning"""
    agent: Agent
    score: float
    reasoning: List[str]
    match_factors: Dict[str, float]


class AgentDiscoveryService:
    """Enhanced service for agent discovery and recommendations"""
    
    def __init__(self):
        self.similarity_weights = {
            'tech_stack': 0.4,
            'role_compatibility': 0.3,
            'lifecycle_phase': 0.2,
            'popularity': 0.1
        }
    
    async def get_personalized_recommendations(
        self, 
        context: DiscoveryContext, 
        limit: int = 10
    ) -> List[AgentRecommendation]:
        """Get personalized agent recommendations based on user context"""
        async with get_async_session() as session:
            # Get base agent pool
            agents = await self._get_candidate_agents(session, context)
            
            # Score each agent
            recommendations = []
            for agent in agents:
                score, reasoning, factors = await self._score_agent_for_context(
                    session, agent, context
                )
                
                if score > 0.3:  # Minimum relevance threshold
                    recommendations.append(AgentRecommendation(
                        agent=agent,
                        score=score,
                        reasoning=reasoning,
                        match_factors=factors
                    ))
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:limit]
    
    async def get_similar_agents(
        self, 
        agent_id: int, 
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """Get agents similar to the specified agent"""
        async with get_async_session() as session:
            target_agent = await Agent.get_by_id(session, agent_id)
            if not target_agent:
                return []
            
            # Find similar agents based on multiple factors
            similar_agents = []
            
            # 1. Tech stack similarity
            tech_similar = await self._find_tech_similar_agents(
                session, target_agent, limit * 2
            )
            
            # 2. Role similarity
            role_similar = await self._find_role_similar_agents(
                session, target_agent, limit * 2
            )
            
            # 3. Repository similarity (same source)
            repo_similar = await self._find_repository_similar_agents(
                session, target_agent, limit
            )
            
            # Combine and score similarities
            all_candidates = {}
            
            # Add tech similar agents
            for agent, similarity in tech_similar:
                if agent.id not in all_candidates:
                    all_candidates[agent.id] = {
                        'agent': agent,
                        'scores': {'tech': similarity, 'role': 0, 'repo': 0}
                    }
                else:
                    all_candidates[agent.id]['scores']['tech'] = similarity
            
            # Add role similar agents
            for agent, similarity in role_similar:
                if agent.id not in all_candidates:
                    all_candidates[agent.id] = {
                        'agent': agent,
                        'scores': {'tech': 0, 'role': similarity, 'repo': 0}
                    }
                else:
                    all_candidates[agent.id]['scores']['role'] = similarity
            
            # Add repository similar agents
            for agent in repo_similar:
                if agent.id not in all_candidates:
                    all_candidates[agent.id] = {
                        'agent': agent,
                        'scores': {'tech': 0, 'role': 0, 'repo': 0.7}
                    }
                else:
                    all_candidates[agent.id]['scores']['repo'] = 0.7
            
            # Calculate combined scores
            for candidate_id, data in all_candidates.items():
                scores = data['scores']
                combined_score = (
                    scores['tech'] * 0.5 + 
                    scores['role'] * 0.3 + 
                    scores['repo'] * 0.2
                )
                data['combined_score'] = combined_score
            
            # Sort by combined score
            sorted_candidates = sorted(
                all_candidates.values(),
                key=lambda x: x['combined_score'],
                reverse=True
            )
            
            # Format results
            for candidate in sorted_candidates[:limit]:
                agent = candidate['agent']
                scores = candidate['scores']
                
                relationship_type = "similar_tech_stack"
                if scores['role'] > scores['tech']:
                    relationship_type = "similar_role"
                elif scores['repo'] > 0:
                    relationship_type = "same_repository"
                
                similar_agents.append({
                    'id': agent.id,
                    'name': agent.name,
                    'description': agent.description,
                    'relationship': relationship_type,
                    'similarity_score': candidate['combined_score'],
                    'shared_technologies': self._get_shared_tech_tags(target_agent, agent),
                    'repository': agent.repository.to_dict() if agent.repository else {}
                })
            
            return similar_agents
    
    async def get_complementary_agents(
        self, 
        selected_agent_ids: List[int], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get agents that complement the already selected ones"""
        if not selected_agent_ids:
            return []
        
        async with get_async_session() as session:
            # Get selected agents
            selected_agents = []
            for agent_id in selected_agent_ids:
                agent = await Agent.get_by_id(session, agent_id)
                if agent:
                    selected_agents.append(agent)
            
            if not selected_agents:
                return []
            
            # Analyze what's missing
            covered_phases = set()
            covered_roles = set()
            covered_tech = set()
            
            for agent in selected_agents:
                if agent.primary_classification:
                    covered_phases.add(agent.primary_classification.lifecycle_phase)
                    covered_roles.add(agent.primary_classification.role_type)
                covered_tech.update(agent.tech_tags)
            
            # Find complementary agents
            complementary_agents = []
            
            # 1. Fill lifecycle gaps
            missing_phases = set(['concept', 'design', 'development', 'testing', 'deployment', 'operations']) - covered_phases
            for phase in missing_phases:
                agents = await Agent.search_and_filter(
                    session,
                    lifecycle_phase=phase,
                    limit=3
                )
                for agent in agents:
                    if agent.id not in selected_agent_ids:
                        complementary_agents.append({
                            'agent': agent,
                            'complement_type': 'lifecycle_gap',
                            'complement_reason': f"Covers {phase} phase"
                        })
            
            # 2. Add specialized roles
            specialized_roles = ['performance-engineer', 'security-specialist', 'devops-engineer']
            missing_roles = set(specialized_roles) - covered_roles
            for role in missing_roles:
                agents = await Agent.search_and_filter(
                    session,
                    role_type=role,
                    limit=2
                )
                for agent in agents:
                    if agent.id not in selected_agent_ids:
                        complementary_agents.append({
                            'agent': agent,
                            'complement_type': 'specialized_role',
                            'complement_reason': f"Adds {role.replace('-', ' ')} expertise"
                        })
            
            # 3. Technology diversity
            all_tech_tags = await TechStack.get_popular_tags(session, limit=20)
            underrepresented_tech = []
            for tech_info in all_tech_tags:
                if tech_info['tag'] not in covered_tech:
                    underrepresented_tech.append(tech_info['tag'])
            
            for tech in underrepresented_tech[:5]:
                agents = await Agent.search_and_filter(
                    session,
                    tech_stack=[tech],
                    limit=2
                )
                for agent in agents:
                    if agent.id not in selected_agent_ids:
                        complementary_agents.append({
                            'agent': agent,
                            'complement_type': 'tech_diversity',
                            'complement_reason': f"Adds {tech} expertise"
                        })
            
            # Score and rank complementary agents
            scored_agents = []
            for item in complementary_agents:
                agent = item['agent']
                score = await self._calculate_complement_score(session, agent, selected_agents)
                
                scored_agents.append({
                    'id': agent.id,
                    'name': agent.name,
                    'description': agent.description,
                    'complement_type': item['complement_type'],
                    'complement_reason': item['complement_reason'],
                    'complement_score': score,
                    'repository': agent.repository.to_dict() if agent.repository else {},
                    'classifications': agent.primary_classification.to_dict() if agent.primary_classification else {}
                })
            
            # Sort by complement score and remove duplicates
            seen_ids = set()
            unique_agents = []
            for agent_data in sorted(scored_agents, key=lambda x: x['complement_score'], reverse=True):
                if agent_data['id'] not in seen_ids:
                    unique_agents.append(agent_data)
                    seen_ids.add(agent_data['id'])
            
            return unique_agents[:limit]
    
    async def get_trending_agents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get currently trending agents based on recent activity"""
        async with get_async_session() as session:
            # Get download statistics for trending calculation
            download_stats = await DownloadSelection.get_download_stats(session, days=7)
            
            # Get recently added popular agents
            stmt = select(Agent).join(Repository).where(
                Agent.is_classified == True
            ).order_by(
                Repository.star_count.desc(),
                Agent.created_at.desc()
            ).limit(limit * 2)
            
            result = await session.execute(stmt)
            agents = result.scalars().all()
            
            # Score agents for trending
            trending_agents = []
            download_map = {stat['agent_id']: stat for stat in download_stats}
            
            for agent in agents:
                download_info = download_map.get(agent.id, {'download_count': 0, 'unique_sessions': 0})
                
                # Calculate trending score
                trending_score = (
                    download_info['download_count'] * 0.4 +
                    download_info['unique_sessions'] * 0.3 +
                    (agent.repository.star_count or 0) * 0.002 +
                    (30 - (datetime.utcnow() - agent.created_at).days) * 0.1  # Recency bonus
                )
                
                trending_agents.append({
                    'agent': agent,
                    'trending_score': trending_score,
                    'download_count': download_info['download_count'],
                    'unique_downloads': download_info['unique_sessions']
                })
            
            # Sort by trending score
            trending_agents.sort(key=lambda x: x['trending_score'], reverse=True)
            
            return [{
                'id': item['agent'].id,
                'name': item['agent'].name,
                'description': item['agent'].description,
                'trending_score': item['trending_score'],
                'download_count': item['download_count'],
                'repository': item['agent'].repository.to_dict() if item['agent'].repository else {},
                'classifications': item['agent'].primary_classification.to_dict() if item['agent'].primary_classification else {}
            } for item in trending_agents[:limit]]
    
    async def _get_candidate_agents(self, session: AsyncSession, context: DiscoveryContext) -> List[Agent]:
        """Get candidate agents based on context"""
        filters = {}
        
        if context.preferred_lifecycle:
            filters['lifecycle_phase'] = context.preferred_lifecycle
        
        if context.preferred_role:
            filters['role_type'] = context.preferred_role
        
        if context.tech_interests:
            filters['tech_stack'] = context.tech_interests
        
        return await Agent.search_and_filter(
            session,
            search=context.search_query,
            **filters,
            limit=50
        )
    
    async def _score_agent_for_context(
        self, 
        session: AsyncSession, 
        agent: Agent, 
        context: DiscoveryContext
    ) -> Tuple[float, List[str], Dict[str, float]]:
        """Score an agent for a given context"""
        score = 0.0
        reasoning = []
        factors = {}
        
        # Tech stack match
        if context.tech_interests:
            tech_overlap = set(agent.tech_tags) & set(context.tech_interests)
            tech_score = len(tech_overlap) / len(context.tech_interests) if context.tech_interests else 0
            score += tech_score * self.similarity_weights['tech_stack']
            factors['tech_match'] = tech_score
            
            if tech_overlap:
                reasoning.append(f"Matches {len(tech_overlap)} of your technology interests")
        
        # Role compatibility
        if context.preferred_role and agent.primary_classification:
            if agent.primary_classification.role_type == context.preferred_role:
                role_score = 1.0
                reasoning.append(f"Exact match for {context.preferred_role} role")
            else:
                role_score = self._calculate_role_compatibility(
                    agent.primary_classification.role_type, 
                    context.preferred_role
                )
                if role_score > 0.5:
                    reasoning.append(f"Compatible with {context.preferred_role} role")
            
            score += role_score * self.similarity_weights['role_compatibility']
            factors['role_match'] = role_score
        
        # Lifecycle phase match
        if context.preferred_lifecycle and agent.primary_classification:
            if agent.primary_classification.lifecycle_phase == context.preferred_lifecycle:
                lifecycle_score = 1.0
                reasoning.append(f"Perfect for {context.preferred_lifecycle} phase")
            else:
                lifecycle_score = 0.3  # Partial match
            
            score += lifecycle_score * self.similarity_weights['lifecycle_phase']
            factors['lifecycle_match'] = lifecycle_score
        
        # Popularity/quality score
        popularity_score = min((agent.repository.star_count or 0) / 1000, 1.0) if agent.repository else 0
        score += popularity_score * self.similarity_weights['popularity']
        factors['popularity'] = popularity_score
        
        # Experience level appropriateness
        if agent.primary_classification:
            confidence = agent.primary_classification.confidence_score
            if context.experience_level == "beginner" and confidence >= 0.8:
                reasoning.append("Well-documented and reliable for beginners")
                score += 0.1
            elif context.experience_level == "advanced" and confidence >= 0.9:
                reasoning.append("High-quality implementation for advanced users")
                score += 0.1
        
        return score, reasoning, factors
    
    async def _find_tech_similar_agents(
        self, 
        session: AsyncSession, 
        target_agent: Agent, 
        limit: int
    ) -> List[Tuple[Agent, float]]:
        """Find agents with similar technology stacks"""
        if not target_agent.tech_tags:
            return []
        
        # Find agents with overlapping tech stacks
        stmt = select(TechStack.agent_id, func.count(TechStack.id).label('overlap_count')).where(
            and_(
                TechStack.tag.in_(target_agent.tech_tags),
                TechStack.agent_id != target_agent.id
            )
        ).group_by(TechStack.agent_id).order_by(func.count(TechStack.id).desc()).limit(limit)
        
        result = await session.execute(stmt)
        similar_agent_data = result.all()
        
        similar_agents = []
        for agent_id, overlap_count in similar_agent_data:
            agent = await Agent.get_by_id(session, agent_id)
            if agent and agent.is_classified:
                similarity = overlap_count / len(target_agent.tech_tags)
                similar_agents.append((agent, similarity))
        
        return similar_agents
    
    async def _find_role_similar_agents(
        self, 
        session: AsyncSession, 
        target_agent: Agent, 
        limit: int
    ) -> List[Tuple[Agent, float]]:
        """Find agents with similar roles"""
        if not target_agent.primary_classification:
            return []
        
        target_role = target_agent.primary_classification.role_type
        target_lifecycle = target_agent.primary_classification.lifecycle_phase
        
        # Find agents with same or compatible roles
        similar_agents = await Agent.search_and_filter(
            session,
            role_type=target_role,
            limit=limit * 2
        )
        
        result = []
        for agent in similar_agents:
            if agent.id != target_agent.id and agent.primary_classification:
                similarity = 1.0 if agent.primary_classification.role_type == target_role else 0.7
                
                # Bonus for same lifecycle phase
                if agent.primary_classification.lifecycle_phase == target_lifecycle:
                    similarity += 0.2
                
                result.append((agent, min(similarity, 1.0)))
        
        return result[:limit]
    
    async def _find_repository_similar_agents(
        self, 
        session: AsyncSession, 
        target_agent: Agent, 
        limit: int
    ) -> List[Agent]:
        """Find agents from the same repository"""
        if not target_agent.repository:
            return []
        
        agents = await Agent.search_and_filter(
            session,
            repository_id=target_agent.repository.id,
            limit=limit * 2
        )
        
        return [agent for agent in agents if agent.id != target_agent.id][:limit]
    
    def _get_shared_tech_tags(self, agent1: Agent, agent2: Agent) -> List[str]:
        """Get shared technology tags between two agents"""
        return list(set(agent1.tech_tags) & set(agent2.tech_tags))
    
    def _calculate_role_compatibility(self, role1: str, role2: str) -> float:
        """Calculate compatibility score between two roles"""
        # Define role compatibility matrix
        compatibility_matrix = {
            'system-architect': {
                'backend-developer': 0.8,
                'devops-engineer': 0.7,
                'database-developer': 0.6
            },
            'backend-developer': {
                'api-designer': 0.9,
                'database-developer': 0.8,
                'performance-engineer': 0.7
            },
            'frontend-developer': {
                'ui-ux-designer': 0.9,
                'performance-engineer': 0.6
            },
            'qa-tester': {
                'performance-engineer': 0.7,
                'security-specialist': 0.6
            }
        }
        
        if role1 in compatibility_matrix and role2 in compatibility_matrix[role1]:
            return compatibility_matrix[role1][role2]
        elif role2 in compatibility_matrix and role1 in compatibility_matrix[role2]:
            return compatibility_matrix[role2][role1]
        else:
            return 0.3  # Default compatibility for unrelated roles
    
    async def _calculate_complement_score(
        self, 
        session: AsyncSession, 
        candidate: Agent, 
        selected_agents: List[Agent]
    ) -> float:
        """Calculate how well a candidate complements selected agents"""
        score = 0.0
        
        # Phase coverage bonus
        covered_phases = {agent.primary_classification.lifecycle_phase for agent in selected_agents if agent.primary_classification}
        if candidate.primary_classification and candidate.primary_classification.lifecycle_phase not in covered_phases:
            score += 0.4
        
        # Role diversity bonus
        covered_roles = {agent.primary_classification.role_type for agent in selected_agents if agent.primary_classification}
        if candidate.primary_classification and candidate.primary_classification.role_type not in covered_roles:
            score += 0.3
        
        # Tech diversity bonus
        covered_tech = set()
        for agent in selected_agents:
            covered_tech.update(agent.tech_tags)
        
        unique_tech = set(candidate.tech_tags) - covered_tech
        tech_diversity_bonus = len(unique_tech) / max(len(candidate.tech_tags), 1)
        score += tech_diversity_bonus * 0.3
        
        return score


from datetime import datetime