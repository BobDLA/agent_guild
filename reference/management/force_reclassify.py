#!/usr/bin/env python3
"""
Force reclassify agents by marking them as unclassified first
"""

import asyncio
import sys
from datetime import datetime

from app.services.classification import ClassificationService
from app.core.database import get_async_session
from app.models.agent import Agent

async def force_reclassify():
    """Force reclassification by marking all agents as unclassified first"""
    print("🚀 Force Reclassifying Agents with Claude CLI")
    print("=" * 50)
    
    try:
        async with get_async_session() as session:
            # Get all agents and mark them as unclassified
            from sqlalchemy import select, update
            
            # Update all agents to be unclassified
            update_stmt = update(Agent).values(is_classified=False)
            await session.execute(update_stmt)
            await session.commit()
            
            print("📝 Marked all agents as unclassified")
            
            # Now run classification
            classification_service = ClassificationService()
            
            # Test with just a few agents first
            results = await classification_service.classify_all_agents()
            
            print(f"🎯 Classification Results:")
            print(f"   ✅ Successfully classified: {results['success']}")
            print(f"   📋 Needs manual review: {results['needs_review']}")
            print(f"   ⚠️  Low confidence (general): {results['skipped']}")
            print(f"   ❌ Failed: {results['failed']}")
            print(f"   📊 Total agents processed: {results['total']}")
            
            return results['success'] > 0
            
    except Exception as e:
        print(f"\n💥 Force reclassification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(force_reclassify())
    if not success:
        sys.exit(1)