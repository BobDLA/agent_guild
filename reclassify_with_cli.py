#!/usr/bin/env python3
"""
Reclassify all agents using Claude CLI
"""

import asyncio
import sys
from datetime import datetime

from app.services.classification import ClassificationService
from app.core.database import get_async_session
from app.models.agent import Agent

async def reclassify_all_agents():
    """Reclassify all agents using Claude CLI"""
    print("🚀 Reclassifying All Agents with Claude CLI")
    print("=" * 50)
    
    start_time = datetime.now()
    
    try:
        # Run a smaller batch first to test
        classification_service = ClassificationService()
        classify_results = await classification_service.classify_all_agents()
        
        print(f"🎯 Classification Results:")
        print(f"   ✅ Successfully classified: {classify_results['success']}")
        print(f"   📋 Needs manual review: {classify_results['needs_review']}")
        print(f"   ⚠️  Low confidence (general): {classify_results['skipped']}")
        print(f"   ❌ Failed: {classify_results['failed']}")
        print(f"   📊 Total agents processed: {classify_results['total']}")
        
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"   ⏱️  Total time: {duration}")
        
        return classify_results['success'] > 0 or classify_results['needs_review'] > 0
            
    except Exception as e:
        print(f"\n💥 Reclassification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(reclassify_all_agents())
    if not success:
        sys.exit(1)