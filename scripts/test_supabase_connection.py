#!/usr/bin/env python3
"""
Test Supabase connection
"""

import asyncio
import asyncpg
from pathlib import Path

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

async def test_connection():
    """Test connection to Supabase"""
    supabase_url, db_url = load_supabase_config()
    
    print(f"Supabase URL: {supabase_url}")
    print(f"Database URL: {db_url}")
    
    if not db_url:
        print("❌ No database URL found!")
        return
    
    try:
        # Try with SSL parameters
        modified_db_url = db_url + "?sslmode=require"
        print(f"Trying with SSL: {modified_db_url}")
        
        conn = await asyncpg.connect(modified_db_url)
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Connection successful! Result: {result}")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Trying without SSL...")
        
        try:
            conn = await asyncpg.connect(db_url)
            result = await conn.fetchval("SELECT 1")
            print(f"✅ Connection successful without SSL! Result: {result}")
            await conn.close()
        except Exception as e2:
            print(f"❌ Connection failed without SSL: {e2}")

if __name__ == "__main__":
    asyncio.run(test_connection())