#!/usr/bin/env python3
"""
Test script for Claude CLI integration
"""

import asyncio
import sys
from app.services.classification import ClassificationService
from app.core.database import get_async_session
from app.models.agent import Agent

async def test_claude_cli_classification():
    """Test Claude CLI classification on a single agent"""
    print("🧪 Testing Claude CLI Classification")
    print("=" * 40)
    
    try:
        async with get_async_session() as session:
            # Get the first agent for testing
            agents = await Agent.get_unclassified(session, limit=1)
            
            if not agents:
                print("❌ No unclassified agents found for testing")
                # Get any agent for testing
                from sqlalchemy import select
                stmt = select(Agent).limit(1)
                result = await session.execute(stmt)
                agents = result.scalars().all()
                
                if not agents:
                    print("❌ No agents found in database")
                    return False
                
                print("📋 Using classified agent for testing...")
            
            agent = agents[0]
            print(f"🤖 Testing classification for: {agent.name}")
            print(f"📝 Description: {agent.description[:100]}...")
            
            # Test classification
            classification_service = ClassificationService()
            result = await classification_service._classify_agent(agent)
            
            print(f"\n🎯 Classification Results:")
            print(f"   📊 Lifecycle Phase: {result.lifecycle_phase}")
            print(f"   👤 Role Type: {result.role_type}")
            print(f"   📈 Confidence: {result.confidence_score}")
            print(f"   🏷️  Tech Stack: {[ts['tag'] for ts in result.tech_stack]}")
            print(f"   💭 Reasoning: {result.reasoning}")
            print(f"   🔍 Keywords: {result.keywords_found}")
            
            # Check if it's using mock or real classification
            if result.reasoning == "Mock fallback classification when Claude CLI unavailable":
                print("\n⚠️  Using mock classification (Claude CLI failed)")
                return False
            else:
                print("\n✅ Claude CLI classification successful!")
                return True
                
    except Exception as e:
        print(f"\n💥 Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_claude_cli_classification())
    if not success:
        sys.exit(1)