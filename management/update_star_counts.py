#!/usr/bin/env python3
"""
Utility script to update repository star counts from GitHub API
Usage: python update_star_counts.py
"""

import asyncio
import httpx
from app.core.database import get_async_session
from app.models.repository import Repository


async def update_star_counts():
    """Update star counts for all active repositories"""
    print("Updating repository star counts...")
    
    async with get_async_session() as session:
        repos = await Repository.get_all_active(session)
        
        if not repos:
            print("No active repositories found.")
            return
        
        updated_count = 0
        async with httpx.AsyncClient() as client:
            for repo in repos:
                if 'github.com' in repo.url:
                    # Extract GitHub repo name from URL
                    repo_name = repo.url.replace('https://github.com/', '').replace('.git', '')
                    
                    try:
                        print(f"Fetching data for {repo_name}...")
                        response = await client.get(f'https://api.github.com/repos/{repo_name}')
                        
                        if response.status_code == 200:
                            data = response.json()
                            old_stars = repo.star_count or 0
                            new_stars = data.get('stargazers_count', 0)
                            new_forks = data.get('forks_count', 0)
                            
                            # Update repository metadata
                            repo.star_count = new_stars
                            repo.fork_count = new_forks
                            repo.language = data.get('language')
                            repo.license = data.get('license', {}).get('name') if data.get('license') else None
                            
                            print(f"  ✓ {repo.name}: {old_stars} → {new_stars} stars")
                            updated_count += 1
                            
                        elif response.status_code == 403:
                            print(f"  ⚠ Rate limited for {repo_name} (status: {response.status_code})")
                        elif response.status_code == 404:
                            print(f"  ✗ Repository not found: {repo_name}")
                        else:
                            print(f"  ✗ Failed to fetch {repo_name}: HTTP {response.status_code}")
                            
                    except Exception as e:
                        print(f"  ✗ Error updating {repo_name}: {e}")
                else:
                    print(f"  - Skipping non-GitHub repository: {repo.name}")
        
        # Commit all changes
        await session.commit()
        print(f"\n✅ Successfully updated {updated_count} repositories!")


if __name__ == "__main__":
    asyncio.run(update_star_counts())