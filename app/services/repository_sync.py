# Repository synchronization service

import os
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional, Dict, Any
from git import Repo, GitCommandError
from datetime import datetime, timedelta
from sqlalchemy import select, or_

from app.core.database import get_async_session
from app.models.repository import Repository
from config.settings import (
    REPOSITORIES_DIR, 
    CONFIGURED_REPOSITORIES,
    GITHUB_TOKEN,
    GITHUB_API_BASE
)


class RepositorySyncService:
    """Service for synchronizing Git repositories"""
    
    def __init__(self):
        self.repositories_dir = Path(REPOSITORIES_DIR)
        self.repositories_dir.mkdir(exist_ok=True)
        self.github_token = GITHUB_TOKEN
    
    async def sync_all_repositories(self) -> Dict[str, Any]:
        """Synchronize all configured repositories"""
        results = {
            "success": [],
            "failed": [],
            "total": len(CONFIGURED_REPOSITORIES)
        }
        
        async with get_async_session() as session:
            for repo_config in CONFIGURED_REPOSITORIES:
                try:
                    await self._sync_single_repository(session, repo_config)
                    results["success"].append(repo_config["name"])
                except Exception as e:
                    print(f"Failed to sync {repo_config['name']}: {str(e)}")
                    results["failed"].append({
                        "name": repo_config["name"],
                        "error": str(e)
                    })
        
        return results
    
    async def sync_repository(self, repository_name: str) -> bool:
        """Synchronize a specific repository by name"""
        repo_config = None
        for config in CONFIGURED_REPOSITORIES:
            if config["name"] == repository_name:
                repo_config = config
                break
        
        if not repo_config:
            raise ValueError(f"Repository {repository_name} not found in configuration")
        
        async with get_async_session() as session:
            await self._sync_single_repository(session, repo_config)
            return True
    
    async def _sync_single_repository(self, session, repo_config: Dict[str, str]):
        """Synchronize a single repository"""
        repo_name = repo_config["name"]
        repo_url = repo_config["url"]
        repo_path = self.repositories_dir / repo_name.replace("/", "_")
        
        print(f"Syncing repository: {repo_name}")
        
        # Get or create repository record
        db_repo = await Repository.get_by_name(session, repo_name)
        if not db_repo:
            db_repo = await Repository.create(
                session,
                name=repo_name,
                url=repo_url,
                description=repo_config.get("description", ""),
                submodule_path=str(repo_path)
            )
        
        # Clone or update repository
        if repo_path.exists():
            await self._update_repository(repo_path)
        else:
            await self._clone_repository(repo_url, repo_path)
        
        # Update GitHub metadata
        github_metadata = await self._fetch_github_metadata(repo_name)
        if github_metadata:
            await db_repo.update_github_metadata(session, github_metadata)
            print(f"Updated GitHub metadata for {repo_name}: {github_metadata.get('stargazers_count', 0)} stars")
        else:
            print(f"Could not fetch GitHub metadata for {repo_name}")
        
        # Mark as synced
        await db_repo.mark_synced(session)
        
        print(f"Successfully synced: {repo_name}")
    
    async def _clone_repository(self, repo_url: str, repo_path: Path):
        """Clone a repository"""
        try:
            # Run git clone in a thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Repo.clone_from(repo_url, repo_path, depth=1)
            )
            print(f"Cloned repository to {repo_path}")
        except GitCommandError as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    async def _update_repository(self, repo_path: Path):
        """Update an existing repository"""
        try:
            repo = Repo(repo_path)
            
            # Run git pull in a thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: repo.remotes.origin.pull()
            )
            print(f"Updated repository at {repo_path}")
        except GitCommandError as e:
            raise Exception(f"Failed to update repository: {str(e)}")
    
    async def _fetch_github_metadata(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Fetch repository metadata from GitHub API"""
        if not self.github_token:
            return None
        
        url = f"{GITHUB_API_BASE}/repos/{repo_name}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    print(f"Rate limited when fetching metadata for {repo_name}")
                    return None
                else:
                    print(f"Failed to fetch GitHub metadata for {repo_name}: {response.status_code}")
                    return None
        except Exception as e:
            print(f"Error fetching GitHub metadata for {repo_name}: {str(e)}")
            return None
    
    async def get_repository_files(self, repository_name: str, extensions: List[str] = None) -> List[Path]:
        """Get all files from a repository with specified extensions"""
        if extensions is None:
            extensions = [".md", ".markdown"]
        
        repo_path = self.repositories_dir / repository_name.replace("/", "_")
        
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository {repository_name} not found locally")
        
        files = []
        for ext in extensions:
            files.extend(repo_path.rglob(f"*{ext}"))
        
        return files
    
    async def cleanup_old_repositories(self, keep_days: int = 30):
        """Clean up repositories that haven't been synced recently"""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        async with get_async_session() as session:
            # Get repositories that haven't been synced recently
            stmt = select(Repository).where(
                or_(
                    Repository.last_synced_at < cutoff_date,
                    Repository.last_synced_at.is_(None)
                )
            )
            result = await session.execute(stmt)
            old_repos = result.scalars().all()
            
            for repo in old_repos:
                repo_path = Path(repo.submodule_path) if repo.submodule_path else None
                
                if repo_path and repo_path.exists():
                    # Remove directory
                    import shutil
                    shutil.rmtree(repo_path)
                    print(f"Cleaned up old repository: {repo.name}")
                
                # Mark as inactive
                repo.is_active = False
                await session.flush()
    
    def get_repository_path(self, repository_name: str) -> Path:
        """Get the local path for a repository"""
        return self.repositories_dir / repository_name.replace("/", "_")
    
    def list_local_repositories(self) -> List[str]:
        """List all locally available repositories"""
        if not self.repositories_dir.exists():
            return []
        
        return [
            d.name for d in self.repositories_dir.iterdir() 
            if d.is_dir() and not d.name.startswith(".")
        ]