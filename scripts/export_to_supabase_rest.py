#!/usr/bin/env python3
"""
SQLite to Supabase Export Script using Supabase Client

This script exports data from the local SQLite database to Supabase using the REST API.
"""

import sqlite3
import json
import sys
from pathlib import Path
from supabase import create_client, Client
import time

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
    supabase_key = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('SUPABASE_URL='):
            supabase_url = line.split('=', 1)[1]
        elif line.startswith('SUPABASE_ANON_KEY='):
            supabase_key = line.split('=', 1)[1]
    
    return supabase_url, supabase_key

def export_sqlite_to_supabase():
    """Export local SQLite data to Supabase using REST API"""
    
    # Load configuration
    supabase_url, supabase_key = load_supabase_config()
    if not supabase_url or not supabase_key:
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
    print(f"☁️  Supabase URL: {supabase_url}")
    
    try:
        # Initialize Supabase client
        print("🔌 Connecting to Supabase...")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test connection
        try:
            response = supabase.table('repositories').select('count', count='exact').limit(1).execute()
            print("✅ Connected to Supabase successfully!")
        except Exception as e:
            print(f"⚠️  Connection test failed, but continuing: {e}")
        
        # Export data in order to respect foreign key constraints
        export_repositories(sqlite_conn, supabase)
        export_agents(sqlite_conn, supabase)
        export_classifications(sqlite_conn, supabase)
        export_tech_stacks(sqlite_conn, supabase)
        
        print("🎉 Data export completed successfully!")
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        sqlite_conn.close()

def export_repositories(sqlite_conn, supabase):
    """Export repositories data"""
    print("📦 Exporting repositories...")
    
    # Get repositories from SQLite
    repos = sqlite_conn.execute("SELECT * FROM repositories").fetchall()
    print(f"   Found {len(repos)} repositories")
    
    exported_count = 0
    for repo in repos:
        try:
            repo_data = {
                'id': repo['id'],
                'name': repo['name'],
                'url': repo['url'],
                'description': repo['description'],
                'star_count': repo['star_count'] or 0,
                'fork_count': repo['fork_count'] or 0,
                'language': repo['language'],
                'license': repo['license'],
                'is_active': bool(repo['is_active']),
                'submodule_path': repo['submodule_path'],
                'created_at': repo['created_at'],
                'updated_at': repo['updated_at'],
                'last_synced_at': repo['last_synced_at']
            }
            
            # Check if repository exists
            existing = supabase.table('repositories').select('*').eq('id', repo['id']).execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('repositories').update(repo_data).eq('id', repo['id']).execute()
            else:
                # Insert new
                result = supabase.table('repositories').insert(repo_data).execute()
            
            if result.data:
                exported_count += 1
            else:
                print(f"   ⚠️  Failed to export repository {repo['name']}: {result}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ Failed to export repository {repo['name']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(repos)} repositories")

def export_agents(sqlite_conn, supabase):
    """Export agents data"""
    print("🤖 Exporting agents...")
    
    # Get agents from SQLite
    agents = sqlite_conn.execute("SELECT * FROM agents").fetchall()
    print(f"   Found {len(agents)} agents")
    
    exported_count = 0
    for agent in agents:
        try:
            # Convert JSON string to JSON if needed
            yaml_metadata = agent['yaml_metadata']
            if isinstance(yaml_metadata, str):
                try:
                    yaml_metadata = json.loads(yaml_metadata)
                except json.JSONDecodeError:
                    yaml_metadata = {}
            
            agent_data = {
                'id': agent['id'],
                'name': agent['name'],
                'description': agent['description'],
                'file_path': agent['file_path'],
                'repository_id': agent['repository_id'],
                'system_prompt': agent['system_prompt'],
                'yaml_metadata': yaml_metadata,
                'content_hash': agent['content_hash'],
                'is_parsed': bool(agent['is_parsed']),
                'is_classified': bool(agent['is_classified']),
                'created_at': agent['created_at'],
                'updated_at': agent['updated_at'],
                'parsed_at': agent['parsed_at']
            }
            
            # Check if agent exists
            existing = supabase.table('agents').select('*').eq('id', agent['id']).execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('agents').update(agent_data).eq('id', agent['id']).execute()
            else:
                # Insert new
                result = supabase.table('agents').insert(agent_data).execute()
            
            if result.data:
                exported_count += 1
            else:
                print(f"   ⚠️  Failed to export agent {agent['name']}: {result}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ Failed to export agent {agent['name']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(agents)} agents")

def export_classifications(sqlite_conn, supabase):
    """Export classifications data"""
    print("🏷️  Exporting classifications...")
    
    # Get classifications from SQLite
    classifications = sqlite_conn.execute("SELECT * FROM classifications").fetchall()
    print(f"   Found {len(classifications)} classifications")
    
    exported_count = 0
    for classification in classifications:
        try:
            classification_data = {
                'id': classification['id'],
                'agent_id': classification['agent_id'],
                'lifecycle_phase': classification['lifecycle_phase'],
                'role_type': classification['role_type'],
                'confidence_score': float(classification['confidence_score']),
                'is_ai_generated': bool(classification['is_ai_generated']),
                'is_reviewed': bool(classification['is_reviewed']),
                'reviewed_by': classification['reviewed_by'],
                'review_notes': classification['review_notes'],
                'created_at': classification['created_at'],
                'classified_at': classification['classified_at'],
                'reviewed_at': classification['reviewed_at']
            }
            
            # Check if classification exists
            existing = supabase.table('classifications').select('*').eq('id', classification['id']).execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('classifications').update(classification_data).eq('id', classification['id']).execute()
            else:
                # Insert new
                result = supabase.table('classifications').insert(classification_data).execute()
            
            if result.data:
                exported_count += 1
            else:
                print(f"   ⚠️  Failed to export classification {classification['id']}: {result}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ Failed to export classification {classification['id']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(classifications)} classifications")

def export_tech_stacks(sqlite_conn, supabase):
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
            tech_stack_data = {
                'id': tech_stack['id'],
                'agent_id': tech_stack['agent_id'],
                'tag': tech_stack['tag'],
                'category': tech_stack['category'] or 'general',
                'created_at': tech_stack['created_at']
            }
            
            # Check if tech stack exists
            existing = supabase.table('tech_stacks').select('*').eq('id', tech_stack['id']).execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('tech_stacks').update(tech_stack_data).eq('id', tech_stack['id']).execute()
            else:
                # Insert new
                result = supabase.table('tech_stacks').insert(tech_stack_data).execute()
            
            if result.data:
                exported_count += 1
            else:
                print(f"   ⚠️  Failed to export tech stack {tech_stack['id']}: {result}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ Failed to export tech stack {tech_stack['id']}: {e}")
    
    print(f"   ✅ Exported {exported_count}/{len(tech_stacks)} tech stack entries")

def verify_export(supabase):
    """Verify that data was exported correctly"""
    print("🔍 Verifying export...")
    
    try:
        # Check record counts
        repo_count = supabase.table('repositories').select('*', count='exact').execute()
        agent_count = supabase.table('agents').select('*', count='exact').execute()
        classification_count = supabase.table('classifications').select('*', count='exact').execute()
        tech_stack_count = supabase.table('tech_stacks').select('*', count='exact').execute()
        
        print(f"   📊 Supabase data counts:")
        print(f"      Repositories: {repo_count.count}")
        print(f"      Agents: {agent_count.count}")
        print(f"      Classifications: {classification_count.count}")
        print(f"      Tech Stacks: {tech_stack_count.count}")
        
        return {
            'repositories': repo_count.count,
            'agents': agent_count.count,
            'classifications': classification_count.count,
            'tech_stacks': tech_stack_count.count
        }
        
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting SQLite to Supabase export (REST API)...")
    print("=" * 50)
    
    # Run the export
    export_sqlite_to_supabase()