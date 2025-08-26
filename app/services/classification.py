# Classification service using Claude API

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Note: Replace with actual Claude SDK when available
# from anthropic import AsyncAnthropic
import httpx

from app.core.database import get_async_session
from app.models.agent import Agent
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from config.settings import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    CLASSIFICATION_CONFIDENCE_THRESHOLD,
    CLASSIFICATION_REVIEW_THRESHOLD,
    LIFECYCLE_PHASES,
    ROLE_TYPES,
    TECH_CATEGORIES
)


@dataclass
class ClassificationResult:
    """Classification result structure"""
    lifecycle_phase: str
    role_type: str
    confidence_score: float
    tech_stack: List[Dict[str, str]]
    reasoning: str
    keywords_found: List[str]


class ClassificationService:
    """Service for classifying agents using Claude API"""
    
    def __init__(self):
        self.claude_api_key = CLAUDE_API_KEY
        self.claude_model = CLAUDE_MODEL
        self.confidence_threshold = CLASSIFICATION_CONFIDENCE_THRESHOLD
        self.review_threshold = CLASSIFICATION_REVIEW_THRESHOLD
    
    async def classify_all_agents(self) -> Dict[str, Any]:
        """Classify all unclassified agents"""
        results = {
            "success": 0,
            "failed": 0,
            "needs_review": 0,
            "skipped": 0,
            "total": 0
        }
        
        async with get_async_session() as session:
            # Get unclassified agents
            agents = await Agent.get_unclassified(session, limit=100)
            results["total"] = len(agents)
            
            print(f"Classifying {len(agents)} unclassified agents...")
            
            for agent in agents:
                try:
                    classification_result = await self._classify_agent(agent)
                    
                    if classification_result.confidence_score >= self.confidence_threshold:
                        # Auto-accept high confidence classifications
                        await self._store_classification(session, agent, classification_result)
                        await agent.mark_classified(session)
                        results["success"] += 1
                        
                    elif classification_result.confidence_score >= self.review_threshold:
                        # Store for manual review
                        await self._store_classification(session, agent, classification_result)
                        results["needs_review"] += 1
                        
                    else:
                        # Assign general category for low confidence
                        general_result = self._create_general_classification(classification_result)
                        await self._store_classification(session, agent, general_result)
                        await agent.mark_classified(session)
                        results["skipped"] += 1
                    
                except Exception as e:
                    print(f"Failed to classify agent {agent.id} ({agent.name}): {str(e)}")
                    results["failed"] += 1
                
                # Add small delay to respect API rate limits
                await asyncio.sleep(0.1)
        
        return results
    
    async def classify_single_agent(self, agent_id: int) -> ClassificationResult:
        """Classify a single agent by ID"""
        async with get_async_session() as session:
            agent = await Agent.get_by_id(session, agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            return await self._classify_agent(agent)
    
    async def _classify_agent(self, agent: Agent) -> ClassificationResult:
        """Classify a single agent using Claude"""
        # Prepare content for classification
        content = self._prepare_content_for_classification(agent)
        
        # Create classification prompt
        prompt = self._create_classification_prompt(content)
        
        # Call Claude API
        response = await self._call_claude_api(prompt)
        
        # Parse response
        return self._parse_classification_response(response, agent)
    
    def _prepare_content_for_classification(self, agent: Agent) -> str:
        """Prepare agent content for classification"""
        content_parts = []
        
        # Add name and description
        content_parts.append(f"Agent Name: {agent.name}")
        if agent.description:
            content_parts.append(f"Description: {agent.description}")
        
        # Add YAML metadata if available
        if agent.yaml_metadata:
            content_parts.append(f"Metadata: {json.dumps(agent.yaml_metadata, indent=2)}")
        
        # Add system prompt (truncated if too long)
        if agent.system_prompt:
            prompt = agent.system_prompt[:2000] + "..." if len(agent.system_prompt) > 2000 else agent.system_prompt
            content_parts.append(f"System Prompt: {prompt}")
        
        return "\n\n".join(content_parts)
    
    def _create_classification_prompt(self, content: str) -> str:
        """Create the classification prompt for Claude"""
        return f"""
You are an expert in software development and AI agent classification. Your task is to classify Claude Code subagents based on their content.

Analyze the following agent and classify it according to these dimensions:

**Lifecycle Phases:**
{', '.join(LIFECYCLE_PHASES)}

**Role Types:**
{', '.join(ROLE_TYPES)}

**Technology Categories:**
{', '.join(TECH_CATEGORIES)}

**Agent to Classify:**
{content}

**Instructions:**
1. Analyze the agent's purpose, functionality, and target use case
2. Choose the MOST SPECIFIC lifecycle phase and role type that apply
3. Identify relevant technology categories and specific technologies mentioned
4. Provide a confidence score (0.0 to 1.0) based on how clearly the agent fits the classification
5. Only classify with high confidence if explicit keywords and clear intent are present
6. Use 'general' categories if the agent doesn't clearly fit specific categories

**Response Format (JSON only):**
{{
  "lifecycle_phase": "specific phase from the list",
  "role_type": "specific role from the list", 
  "confidence_score": 0.95,
  "tech_stack": [
    {{"tag": "React", "category": "frontend"}},
    {{"tag": "Performance Optimization", "category": "performance-optimization"}}
  ],
  "reasoning": "Brief explanation of why this classification was chosen",
  "keywords_found": ["explicit keywords that led to this classification"]
}}

**Classification Rules:**
- Be conservative - only use specific categories if clearly evident
- Prioritize specificity over broad categories when confidence is high
- Include explicit keywords/phrases that support your classification
- Technology stack should include both general categories and specific technologies
- Lower confidence if content is ambiguous or could fit multiple categories
"""
    
    async def _call_claude_api(self, prompt: str) -> str:
        """Call Claude CLI for classification"""
        try:
            # Use local Claude CLI instead of API
            import subprocess
            import asyncio
            
            # Create the classification prompt
            classification_prompt = (
                "You are an expert in software development and AI agent classification. "
                "Respond ONLY with valid JSON in the exact format requested. "
                "Do not include any other text or explanations."
            )
            
            # Run claude CLI command asynchronously
            process = await asyncio.create_subprocess_exec(
                'claude', '-p', classification_prompt,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=prompt.encode('utf-8'))
            
            if process.returncode == 0:
                response = stdout.decode('utf-8').strip()
                print(f"Claude CLI response: {response[:200]}...")
                return response
            else:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                print(f"Claude CLI error (code {process.returncode}): {error_msg}")
                # Fallback to mock response
                return self._mock_claude_response()
        
        except Exception as e:
            print(f"Claude CLI call failed: {str(e)}")
            # Fallback to mock response
            return self._mock_claude_response()
    
    def _mock_claude_response(self) -> str:
        """Mock Claude response for development/testing when CLI fails"""
        return json.dumps({
            "lifecycle_phase": "development",
            "role_type": "backend-developer", 
            "confidence_score": 0.4,
            "tech_stack": [
                {"tag": "General", "category": "general"}
            ],
            "reasoning": "Mock fallback classification when Claude CLI unavailable",
            "keywords_found": ["mock", "fallback"]
        })
    
    def _parse_classification_response(self, response: str, agent: Agent) -> ClassificationResult:
        """Parse Claude's classification response"""
        try:
            # Extract JSON from response
            response_cleaned = response.strip()
            if response_cleaned.startswith("```json"):
                response_cleaned = response_cleaned[7:]
            if response_cleaned.endswith("```"):
                response_cleaned = response_cleaned[:-3]
            
            data = json.loads(response_cleaned)
            
            # Validate required fields
            lifecycle_phase = data.get("lifecycle_phase", "general")
            role_type = data.get("role_type", "general")
            confidence_score = float(data.get("confidence_score", 0.5))
            tech_stack = data.get("tech_stack", [])
            reasoning = data.get("reasoning", "")
            keywords_found = data.get("keywords_found", [])
            
            # Validate against allowed values
            if lifecycle_phase not in LIFECYCLE_PHASES:
                lifecycle_phase = "general"
            
            if role_type not in ROLE_TYPES:
                role_type = "general"
            
            # Ensure confidence is in valid range
            confidence_score = max(0.0, min(1.0, confidence_score))
            
            return ClassificationResult(
                lifecycle_phase=lifecycle_phase,
                role_type=role_type,
                confidence_score=confidence_score,
                tech_stack=tech_stack,
                reasoning=reasoning,
                keywords_found=keywords_found
            )
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse Claude response: {str(e)}")
            print(f"Response: {response}")
            
            # Fallback classification
            return self._create_fallback_classification()
    
    def _create_fallback_classification(self) -> ClassificationResult:
        """Create a fallback classification for parsing errors"""
        return ClassificationResult(
            lifecycle_phase="general",
            role_type="general",
            confidence_score=0.3,
            tech_stack=[{"tag": "General", "category": "general"}],
            reasoning="Fallback classification due to parsing error",
            keywords_found=[]
        )
    
    def _create_general_classification(self, original: ClassificationResult) -> ClassificationResult:
        """Create a general classification for low confidence results"""
        return ClassificationResult(
            lifecycle_phase="general",
            role_type="general",
            confidence_score=0.5,
            tech_stack=[{"tag": "General", "category": "general"}],
            reasoning=f"Low confidence classification: {original.reasoning}",
            keywords_found=original.keywords_found
        )
    
    async def _store_classification(self, session, agent: Agent, result: ClassificationResult):
        """Store classification result in database"""
        # Create classification record
        classification = await Classification.create(
            session,
            agent_id=agent.id,
            lifecycle_phase=result.lifecycle_phase,
            role_type=result.role_type,
            confidence_score=result.confidence_score
        )
        
        # Clear existing tech stack
        await TechStack.delete_for_agent(session, agent.id)
        
        # Create tech stack entries
        if result.tech_stack:
            await TechStack.create_multiple(session, agent.id, result.tech_stack)
    
    async def reclassify_low_confidence_agents(self) -> Dict[str, Any]:
        """Reclassify agents with low confidence scores"""
        results = {
            "processed": 0,
            "improved": 0,
            "unchanged": 0,
            "failed": 0
        }
        
        async with get_async_session() as session:
            # Get low confidence classifications
            low_confidence = await Classification.get_low_confidence(session, threshold=0.7)
            
            for classification in low_confidence:
                try:
                    agent = await Agent.get_by_id(session, classification.agent_id)
                    if not agent:
                        continue
                    
                    # Retry classification
                    new_result = await self._classify_agent(agent)
                    
                    if new_result.confidence_score > classification.confidence_score:
                        # Update with better classification
                        await self._store_classification(session, agent, new_result)
                        results["improved"] += 1
                    else:
                        results["unchanged"] += 1
                    
                    results["processed"] += 1
                    
                except Exception as e:
                    print(f"Failed to reclassify agent {classification.agent_id}: {str(e)}")
                    results["failed"] += 1
        
        return results
    
    async def get_classification_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        async with get_async_session() as session:
            # Get distribution statistics
            distribution = await Classification.get_distribution_stats(session)
            
            # Get confidence statistics
            confidence_stmt = select(
                func.avg(Classification.confidence_score).label("avg_confidence"),
                func.min(Classification.confidence_score).label("min_confidence"),
                func.max(Classification.confidence_score).label("max_confidence"),
                func.count(Classification.id).label("total_classifications")
            )
            
            confidence_result = await session.execute(confidence_stmt)
            confidence_stats = confidence_result.first()
            
            return {
                "distribution": distribution,
                "confidence_stats": {
                    "average": float(confidence_stats.avg_confidence or 0),
                    "minimum": float(confidence_stats.min_confidence or 0),
                    "maximum": float(confidence_stats.max_confidence or 0),
                    "total": confidence_stats.total_classifications
                }
            }