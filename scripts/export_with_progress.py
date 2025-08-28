#!/usr/bin/env python3
"""
Enhanced export script with progress tracking
"""
import sqlite3
import sys
import time
from supabase import create_client
import os

def load_config():
    """Load configuration from environment variables"""
    config = {
        'supabase_url': os.getenv('SUPABASE_URL', 'https://ndysgbprcsbulnpgdpbm.supabase.co'),
        'supabase_key': os.getenv('SUPABASE_KEY'),
        'sqlite_path': 'reference/data/db/agents.db'
    }
    
    if not config['supabase_key']:
        print("❌ SUPABASE_KEY environment variable not set")
        sys.exit(1)
        
    return config

def export_with_progress():
    """Export data with progress tracking"""
    config = load_config()
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(config['sqlite_path'])
        supabase = create_client(config['supabase_url'], config['supabase_key'])
        
        print("🚀 Starting enhanced SQLite to Supabase export...")
        print(f"📊 SQLite DB: {config['sqlite_path']}")
        print(f"☁️  Supabase URL: {config['supabase_url']}")
        
        # Test connection
        try:
            test_response = supabase.table('repositories').select('count', count='exact').limit(1).execute()
            print(f"✅ Connected to Supabase! Current count: {test_response.count}")
        except Exception as e:
            print(f"⚠️  Connection test: {e}")
        
        # Export with timing
        start_time = time.time()
        
        # Step 1: Export repositories
        print("\n📦 Step 1: Exporting repositories...")
        export_repositories_with_progress(sqlite_conn, supabase)
        
        # Step 2: Export agents
        print("\n🤖 Step 2: Exporting agents...")
        export_agents_with_progress(sqlite_conn, supabase)
        
        # Step 3: Export classifications
        print("\n🏷️  Step 3: Exporting classifications...")
        export_classifications_with_progress(sqlite_conn, supabase)
        
        # Step 4: Export tech stacks
        print("\n🛠️  Step 4: Exporting tech stacks...")
        export_tech_stacks_with_progress(sqlite_conn, supabase)
        
        elapsed_time = time.time() - start_time
        print(f"\n🎉 Data export completed successfully in {elapsed_time:.1f} seconds!")
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        sqlite_conn.close()

def export_repositories_with_progress(sqlite_conn, supabase):
    """Export repositories with progress"""
    repos = sqlite_conn.execute("SELECT * FROM repositories").fetchall()
    print(f"   Found {len(repos)} repositories")
    
    exported_count = 0
    for i, repo in enumerate(repos):
        try:
            repo_data = {
                'name': repo[1],
                'url': repo[2],
                'description': repo[3],
                'star_count': repo[4],
                'fork_count': repo[5],
                'language': repo[6],
                'license': repo[7],
                'is_active': bool(repo[8]),
                'submodule_path': repo[9],
                'created_at': repo[10],
                'updated_at': repo[11],
                'last_synced_at': repo[12]
            }
            
            result = supabase.table('repositories').upsert(repo_data).execute()
            exported_count += 1
            
            if i % 10 == 0:
                print(f"   Progress: {exported_count}/{len(repos)} exported")
                
        except Exception as e:
            print(f"   ❌ Failed to export repository {repo[1]}: {e}")
            
    print(f"   ✅ Exported {exported_count}/{len(repos)} repositories")

def export_agents_with_progress(sqlite_conn, supabase):
    """Export agents with progress"""
    agents = sqlite_conn.execute("SELECT * FROM agents").fetchall()
    print(f"   Found {len(agents)} agents")
    
    exported_count = 0
    for i, agent in enumerate(agents):
        try:
            agent_data = {
                'name': agent[1],
                'description': agent[2],
                'file_path': agent[3],
                'repository_id': agent[4],
                'system_prompt': agent[5],
                'yaml_metadata': agent[6],
                'content_hash': agent[7],
                'is_parsed': bool(agent[8]),
                'is_classified': bool(agent[9]),
                'created_at': agent[10],
                'updated_at': agent[11],
                'parsed_at': agent[12]
            }
            
            result = supabase.table('agents').upsert(agent_data).execute()
            exported_count += 1
            
            if i % 50 == 0:
                print(f"   Progress: {exported_count}/{len(agents)} exported")
                
        except Exception as e:
            print(f"   ❌ Failed to export agent {agent[1]}: {e}")
            
    print(f"   ✅ Exported {exported_count}/{len(agents)} agents")

def export_classifications_with_progress(sqlite_conn, supabase):
    """Export classifications with progress"""
    classifications = sqlite_conn.execute("SELECT * FROM classifications").fetchall()
    print(f"   Found {len(classifications)} classifications")
    
    exported_count = 0
    for i, classification in enumerate(classifications):
        try:
            classification_data = {
                'agent_id': classification[1],
                'lifecycle_phase': classification[2],
                'role_type': classification[3],
                'confidence_score': float(classification[4]),
                'is_ai_generated': bool(classification[5]),
                'is_reviewed': bool(classification[6]),
                'reviewed_by': classification[7],
                'review_notes': classification[8],
                'created_at': classification[9],
                'classified_at': classification[10],
                'reviewed_at': classification[11]
            }
            
            result = supabase.table('classifications').upsert(classification_data).execute()
            exported_count += 1
            
            if i % 100 == 0:
                print(f"   Progress: {exported_count}/{len(classifications)} exported")
                
        except Exception as e:
            print(f"   ❌ Failed to export classification: {e}")
            
    print(f"   ✅ Exported {exported_count}/{len(classifications)} classifications")

def export_tech_stacks_with_progress(sqlite_conn, supabase):
    """Export tech stacks with progress"""
    tech_stacks = sqlite_conn.execute("SELECT * FROM tech_stacks").fetchall()
    print(f"   Found {len(tech_stacks)} tech stacks")
    
    exported_count = 0
    for i, tech_stack in enumerate(tech_stacks):
        try:
            tech_stack_data = {
                'agent_id': tech_stack[1],
                'tag': tech_stack[2],
                'category': tech_stack[3],
                'created_at': tech_stack[4]
            }
            
            result = supabase.table('tech_stacks').upsert(tech_stack_data).execute()
            exported_count += 1
            
            if i % 100 == 0:
                print(f"   Progress: {exported_count}/{len(tech_stacks)} exported")
                
        except Exception as e:
            print(f"   ❌ Failed to export tech stack: {e}")
            
    print(f"   ✅ Exported {exported_count}/{len(tech_stacks)} tech stacks")

if __name__ == "__main__":
    export_with_progress()