#!/usr/bin/env python3
"""
SQLite to Supabase PostgreSQL Export Script

This script exports data from the local SQLite database to Supabase PostgreSQL.
It handles data type conversions and preserves relationships between tables.
"""

import sqlite3
import asyncio
import asyncpg
import json
import sys
from datetime import datetime
from pathlib import Path
import os

# Load Supabase configuration
def load_supabase_config():
    """Load Supabase configuration from file"""
    config_path = Path(__file__).parent.parent / "supabase_config"
    if not config_path.exists():
        print("❌ Supabase config file not found!")
        return None, None
    
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Extract configuration
    supabase_url = None
    db_url = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('SUPABASE_URL='):
            supabase_url = line.split('=', 1)[1]
        elif line.startswith('postgresql://'):
            db_url = line
    
    return supabase_url, db_url

async def export_sqlite_to_supabase():
    """Export local SQLite data to Supabase PostgreSQL"""
    
    # Load configuration
    supabase_url, db_url = load_supabase_config()
    if not db_url:
        return
    
    # Local SQLite connection
    sqlite_db_path = Path(__file__).parent.parent / "reference" / "data" / "db" / "agents.db"
    if not sqlite_db_path.exists():
        print(f"❌ SQLite database not found at {sqlite_db_path}")
        return
    
    sqlite_conn = sqlite3.connect(str(sqlite_db_path))
    sqlite_conn.row_factory = sqlite3.Row
    
    print("🚀 Starting data export to Supabase...")
    print(f"📊 SQLite DB: {sqlite_db_path}")
    print(f"☁️  Supabase DB: {db_url}")
    
    try:
        # Connect to Supabase PostgreSQL
        print("🔌 Connecting to Supabase PostgreSQL...")
        pg_conn = await asyncpg.connect(db_url)
        
        # Test connection
        await pg_conn.fetchval("SELECT 1")
        print("✅ Connected to Supabase successfully!")
        
        # Create tables if they don't exist
        await create_tables_if_not_exists(pg_conn)
        
        # Export data in order to respect foreign key constraints
        await export_repositories(sqlite_conn, pg_conn)
        await export_agents(sqlite_conn, pg_conn)
        await export_classifications(sqlite_conn, pg_conn)
        await export_tech_stacks(sqlite_conn, pg_conn)
        
        print("🎉 Data export completed successfully!")
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        if 'pg_conn' in locals():
            await pg_conn.close()
        sqlite_conn.close()

async def create_tables_if_not_exists(pg_conn):
    """Create tables in Supabase if they don't exist"""
    print("🏗️  Creating tables if they don't exist...")
    
    # Create repositories table
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            url VARCHAR(512) NOT NULL,
            description TEXT,
            star_count INTEGER DEFAULT 0,
            fork_count INTEGER DEFAULT 0,
            language VARCHAR(100),
            license VARCHAR(100),
            is_active BOOLEAN DEFAULT true,
            submodule_path VARCHAR(512),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            last_synced_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Create agents table
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            file_path VARCHAR(512) NOT NULL,
            repository_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
            system_prompt TEXT,
            yaml_metadata JSONB,
            content_hash VARCHAR(64),
            is_parsed BOOLEAN DEFAULT false,
            is_classified BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            parsed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Create classifications table
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
            lifecycle_phase VARCHAR(100) NOT NULL,
            role_type VARCHAR(100) NOT NULL,
            confidence_score FLOAT NOT NULL,
            is_ai_generated BOOLEAN DEFAULT true,
            is_reviewed BOOLEAN DEFAULT false,
            reviewed_by VARCHAR(100),
            review_notes VARCHAR(512),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            classified_at TIMESTAMP WITH TIME ZONE NOT NULL,
            reviewed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Create tech_stacks table
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS tech_stacks (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
            tag VARCHAR(100) NOT NULL,
            category VARCHAR(100) DEFAULT 'general',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create indexes for performance
    await pg_conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_repository_id ON agents(repository_id);
        CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
        CREATE INDEX IF NOT EXISTS idx_classifications_agent_id ON classifications(agent_id);
        CREATE INDEX IF NOT EXISTS idx_classifications_lifecycle_phase ON classifications(lifecycle_phase);
        CREATE INDEX IF NOT EXISTS idx_tech_stacks_agent_id ON tech_stacks(agent_id);
    """)
    
    print("✅ Tables created/verified successfully!")

async def export_repositories(sqlite_conn, pg_conn):
    """Export repositories data"""
    print("📦 Exporting repositories...")
    
    # Get repositories from SQLite
    repos = sqlite_conn.execute("SELECT * FROM repositories").fetchall()
    print(f"   Found {len(repos)} repositories")
    
    exported_count = 0
    for repo in repos:
        try:
            await pg_conn.execute("""
                INSERT INTO repositories (
                    id, name, url, description, star_count, fork_count, 
                    language, license, is_active, submodule_path, 
                    created_at, updated_at, last_synced_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    url = EXCLUDED.url,
                    description = EXCLUDED.description,
                    star_count = EXCLUDED.star_count,
                    fork_count = EXCLUDED.fork_count,
                    language = EXCLUDED.language,
                    license = EXCLUDED.license,
                    is_active = EXCLUDED.is_active,
                    submodule_path = EXCLUDED.submodule_path,
                    updated_at = EXCLUDED.updated_at,
                    last_synced_at = EXCLUDED.last_synced_at
            """, 
            repo['id'], repo['name'], repo['url'], repo['description'], 
            repo['star_count'] or 0, repo['fork_count'] or 0,
            repo['language'], repo['license'], repo['is_active'], repo['submodule_path'],
            repo['created_at'], repo['updated_at'], repo['last_synced_at']
            )
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to export repository {repo['name']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(repos)} repositories")

async def export_agents(sqlite_conn, pg_conn):
    """Export agents data"""
    print("🤖 Exporting agents...")
    
    # Get agents from SQLite
    agents = sqlite_conn.execute("SELECT * FROM agents").fetchall()
    print(f"   Found {len(agents)} agents")
    
    exported_count = 0
    for agent in agents:
        try:
            # Convert JSON string to JSONB if needed
            yaml_metadata = agent['yaml_metadata']
            if isinstance(yaml_metadata, str):
                try:
                    yaml_metadata = json.loads(yaml_metadata)
                except json.JSONDecodeError:
                    yaml_metadata = {}
            
            await pg_conn.execute("""
                INSERT INTO agents (
                    id, name, description, file_path, repository_id,
                    system_prompt, yaml_metadata, content_hash,
                    is_parsed, is_classified, created_at, updated_at, parsed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    file_path = EXCLUDED.file_path,
                    repository_id = EXCLUDED.repository_id,
                    system_prompt = EXCLUDED.system_prompt,
                    yaml_metadata = EXCLUDED.yaml_metadata,
                    content_hash = EXCLUDED.content_hash,
                    is_parsed = EXCLUDED.is_parsed,
                    is_classified = EXCLUDED.is_classified,
                    updated_at = EXCLUDED.updated_at,
                    parsed_at = EXCLUDED.parsed_at
            """, 
            agent['id'], agent['name'], agent['description'], agent['file_path'],
            agent['repository_id'], agent['system_prompt'], yaml_metadata,
            agent['content_hash'], agent['is_parsed'], agent['is_classified'],
            agent['created_at'], agent['updated_at'], agent['parsed_at']
            )
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to export agent {agent['name']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(agents)} agents")

async def export_classifications(sqlite_conn, pg_conn):
    """Export classifications data"""
    print("🏷️  Exporting classifications...")
    
    # Get classifications from SQLite
    classifications = sqlite_conn.execute("SELECT * FROM classifications").fetchall()
    print(f"   Found {len(classifications)} classifications")
    
    exported_count = 0
    for classification in classifications:
        try:
            await pg_conn.execute("""
                INSERT INTO classifications (
                    id, agent_id, lifecycle_phase, role_type, confidence_score,
                    is_ai_generated, is_reviewed, reviewed_by, review_notes,
                    created_at, classified_at, reviewed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    agent_id = EXCLUDED.agent_id,
                    lifecycle_phase = EXCLUDED.lifecycle_phase,
                    role_type = EXCLUDED.role_type,
                    confidence_score = EXCLUDED.confidence_score,
                    is_ai_generated = EXCLUDED.is_ai_generated,
                    is_reviewed = EXCLUDED.is_reviewed,
                    reviewed_by = EXCLUDED.reviewed_by,
                    review_notes = EXCLUDED.review_notes,
                    classified_at = EXCLUDED.classified_at,
                    reviewed_at = EXCLUDED.reviewed_at
            """, 
            classification['id'], classification['agent_id'], classification['lifecycle_phase'],
            classification['role_type'], classification['confidence_score'],
            classification['is_ai_generated'], classification['is_reviewed'],
            classification['reviewed_by'], classification['review_notes'],
            classification['created_at'], classification['classified_at'], classification['reviewed_at']
            )
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to export classification {classification['id']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(classifications)} classifications")

async def export_tech_stacks(sqlite_conn, pg_conn):
    """Export tech_stacks data"""
    print("🔧 Exporting tech stacks...")
    
    # Get tech stacks from SQLite
    tech_stacks = sqlite_conn.execute("SELECT * FROM tech_stacks").fetchall()
    print(f"   Found {len(tech_stacks)} tech stack entries")
    
    if not tech_stacks:
        print("   ℹ️  No tech stacks found, skipping...")
        return
    
    exported_count = 0
    for tech_stack in tech_stacks:
        try:
            await pg_conn.execute("""
                INSERT INTO tech_stacks (
                    id, agent_id, tag, category, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    agent_id = EXCLUDED.agent_id,
                    tag = EXCLUDED.tag,
                    category = EXCLUDED.category
            """, 
            tech_stack['id'], tech_stack['agent_id'], tech_stack['tag'],
            tech_stack['category'], tech_stack['created_at']
            )
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to export tech stack {tech_stack['id']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(tech_stacks)} tech stack entries")

async def verify_export(pg_conn):
    """Verify that data was exported correctly"""
    print("🔍 Verifying export...")
    
    # Check record counts
    repo_count = await pg_conn.fetchval("SELECT COUNT(*) FROM repositories")
    agent_count = await pg_conn.fetchval("SELECT COUNT(*) FROM agents")
    classification_count = await pg_conn.fetchval("SELECT COUNT(*) FROM classifications")
    tech_stack_count = await pg_conn.fetchval("SELECT COUNT(*) FROM tech_stacks")
    
    print(f"   📊 Supabase data counts:")
    print(f"      Repositories: {repo_count}")
    print(f"      Agents: {agent_count}")
    print(f"      Classifications: {classification_count}")
    print(f"      Tech Stacks: {tech_stack_count}")
    
    return {
        'repositories': repo_count,
        'agents': agent_count,
        'classifications': classification_count,
        'tech_stacks': tech_stack_count
    }

if __name__ == "__main__":
    # Install required packages if not available
    try:
        import asyncpg
    except ImportError:
        print("Installing required package: asyncpg")
        os.system("pip install asyncpg")
        import asyncpg
    
    print("🚀 Starting SQLite to Supabase export...")
    print("=" * 50)
    
    # Run the export
    asyncio.run(export_sqlite_to_supabase())