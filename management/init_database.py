#!/usr/bin/env python3
"""
Database initialization script for Subagent Guild

This script ensures all models are imported and the database tables are created properly.
"""

import asyncio
import sys
from pathlib import Path

# Import all models to ensure they're registered with SQLAlchemy
from app.models.repository import Repository
from app.models.agent import Agent
from app.models.classification import Classification
from app.models.tech_stack import TechStack
from app.models.download_selection import DownloadSelection

from app.core.database import init_database, Base, engine


async def initialize_database():
    """Initialize the database with all tables"""
    print("🗄️  Initializing Subagent Guild Database")
    print("=" * 50)
    
    try:
        # Check if database file exists
        from config.settings import DATABASE_URL
        print(f"📍 Database URL: {DATABASE_URL}")
        
        # Import all models to ensure they're in the metadata
        print("📦 Importing models...")
        print(f"   ✅ Repository: {Repository.__tablename__}")
        print(f"   ✅ Agent: {Agent.__tablename__}")
        print(f"   ✅ Classification: {Classification.__tablename__}")
        print(f"   ✅ TechStack: {TechStack.__tablename__}")
        print(f"   ✅ DownloadSelection: {DownloadSelection.__tablename__}")
        
        # Create all tables
        print("\n🏗️  Creating database tables...")
        await init_database()
        
        # Verify tables were created
        print("\n🔍 Verifying table creation...")
        async with engine.begin() as conn:
            # Check if tables exist by trying to query them
            from sqlalchemy import text
            
            tables_to_check = [
                "repositories", "agents", "classifications", 
                "tech_stacks", "download_selections"
            ]
            
            for table_name in tables_to_check:
                try:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    print(f"   ✅ {table_name}: {count} records")
                except Exception as e:
                    print(f"   ❌ {table_name}: Error - {str(e)}")
                    return False
        
        print("\n🎉 Database initialization completed successfully!")
        print("📊 All tables are ready for data.")
        return True
        
    except Exception as e:
        print(f"\n💥 Database initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(initialize_database())
    if not success:
        sys.exit(1)