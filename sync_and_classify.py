#!/usr/bin/env python3
"""
Subagent Guild - Repository Sync and Classification Script

This script performs the complete pipeline:
1. Syncs all configured repositories
2. Parses agents from markdown files
3. Classifies agents using AI
"""

import asyncio
import sys
from datetime import datetime

from app.services.repository_sync import RepositorySyncService
from app.services.agent_parser import AgentParserService
from app.services.classification import ClassificationService
from app.core.database import get_async_session


async def main():
    """Run the complete sync and classification pipeline"""
    print("🚀 Starting Subagent Guild Sync & Classification Pipeline")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Step 1: Repository Synchronization
        print("\n📂 Step 1: Synchronizing Repositories")
        print("-" * 40)
        
        sync_service = RepositorySyncService()
        sync_results = await sync_service.sync_all_repositories()
        
        print(f"✅ Synced: {len(sync_results['success'])} repositories")
        for repo in sync_results['success']:
            print(f"   - {repo}")
        
        if sync_results['failed']:
            print(f"❌ Failed: {len(sync_results['failed'])} repositories")
            for failure in sync_results['failed']:
                print(f"   - {failure['name']}: {failure['error']}")
        
        # Step 2: Agent Parsing
        print("\n🧠 Step 2: Parsing Agents from Files")
        print("-" * 40)
        
        parser_service = AgentParserService()
        parse_results = await parser_service.parse_all_agents()
        
        print(f"📊 Parse Results:")
        print(f"   ✅ Successfully parsed: {len(parse_results['success'])}")
        print(f"   ⏭️  Skipped (unchanged): {len(parse_results['skipped'])}")
        print(f"   ❌ Failed: {len(parse_results['failed'])}")
        print(f"   📁 Total files processed: {parse_results['total']}")
        
        if parse_results['failed']:
            print(f"\n❌ Parse Failures:")
            for failure in parse_results['failed'][:5]:  # Show first 5 failures
                print(f"   - {failure.get('file', 'Unknown')}: {failure.get('error', 'Unknown error')}")
            if len(parse_results['failed']) > 5:
                print(f"   ... and {len(parse_results['failed']) - 5} more")
        
        # Step 3: Agent Classification
        print("\n🏷️  Step 3: Classifying Agents")
        print("-" * 40)
        
        classification_service = ClassificationService()
        classify_results = await classification_service.classify_all_agents()
        
        print(f"🎯 Classification Results:")
        print(f"   ✅ Successfully classified: {classify_results['success']}")
        print(f"   📋 Needs manual review: {classify_results['needs_review']}")
        print(f"   ⚠️  Low confidence (general): {classify_results['skipped']}")
        print(f"   ❌ Failed: {classify_results['failed']}")
        print(f"   📊 Total agents processed: {classify_results['total']}")
        
        # Step 4: Final Statistics
        print("\n📈 Step 4: Final Statistics")
        print("-" * 40)
        
        async with get_async_session() as session:
            from app.models.agent import Agent
            from app.models.repository import Repository
            
            total_agents = await Agent.count(session)
            classified_agents = await Agent.count_classified(session)
            active_repos = len(await Repository.get_all_active(session))
            
            print(f"📊 Database Summary:")
            print(f"   🏛️  Active repositories: {active_repos}")
            print(f"   🤖 Total agents: {total_agents}")
            print(f"   ✅ Classified agents: {classified_agents}")
            if total_agents > 0:
                classification_rate = round((classified_agents / total_agents) * 100, 1)
                print(f"   📈 Classification rate: {classification_rate}%")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Pipeline completed successfully!")
        print(f"⏱️  Total time: {duration}")
        print(f"🌐 Service available at: http://127.0.0.1:8000/")
        
    except Exception as e:
        print(f"\n💥 Pipeline failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())