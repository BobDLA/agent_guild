#!/usr/bin/env python3
"""
Subagent Guild - Management CLI

This script handles offline data processing tasks:
- Repository synchronization
- Agent parsing and classification  
- Database management
"""

import click
import asyncio
from pathlib import Path

from app.services.repository_sync import RepositorySyncService
from app.services.agent_parser import AgentParserService  
from app.services.classification import ClassificationService
from app.core.database import init_database


@click.group()
def cli():
    """Subagent Guild management commands"""
    pass


@cli.command()
def init_db():
    """Initialize the database with tables"""
    click.echo("Initializing database...")
    asyncio.run(init_database())
    click.echo("Database initialized successfully!")


@cli.command()
def sync_repos():
    """Synchronize all configured repositories"""
    click.echo("Starting repository synchronization...")
    
    async def run_sync():
        sync_service = RepositorySyncService()
        await sync_service.sync_all_repositories()
    
    asyncio.run(run_sync())
    click.echo("Repository synchronization completed!")


@cli.command()  
def parse_agents():
    """Parse agents from synchronized repositories"""
    click.echo("Starting agent parsing...")
    
    async def run_parse():
        parser_service = AgentParserService()
        await parser_service.parse_all_agents()
    
    asyncio.run(run_parse())
    click.echo("Agent parsing completed!")


@cli.command()
def classify_agents():
    """Classify parsed agents using Claude"""
    click.echo("Starting agent classification...")
    
    async def run_classify():
        classification_service = ClassificationService()
        await classification_service.classify_all_agents()
    
    asyncio.run(run_classify())
    click.echo("Agent classification completed!")


@cli.command()
def process_agents():
    """Full pipeline: sync repos -> parse agents -> classify agents"""
    click.echo("Starting full agent processing pipeline...")
    
    async def run_full_pipeline():
        # Step 1: Sync repositories
        click.echo("Step 1/3: Synchronizing repositories...")
        sync_service = RepositorySyncService()
        await sync_service.sync_all_repositories()
        
        # Step 2: Parse agents
        click.echo("Step 2/3: Parsing agents...")
        parser_service = AgentParserService()
        await parser_service.parse_all_agents()
        
        # Step 3: Classify agents
        click.echo("Step 3/3: Classifying agents...")
        classification_service = ClassificationService()
        await classification_service.classify_all_agents()
    
    asyncio.run(run_full_pipeline())
    click.echo("Full processing pipeline completed!")


@cli.command()
@click.argument('repository_name')
def sync_repo(repository_name):
    """Synchronize a specific repository"""
    click.echo(f"Synchronizing repository: {repository_name}")
    
    async def run_sync_single():
        sync_service = RepositorySyncService()
        await sync_service.sync_repository(repository_name)
    
    asyncio.run(run_sync_single())
    click.echo(f"Repository {repository_name} synchronized!")


@cli.command()
def list_repos():
    """List all configured repositories"""
    from config.settings import CONFIGURED_REPOSITORIES
    
    click.echo("Configured repositories:")
    for repo in CONFIGURED_REPOSITORIES:
        click.echo(f"  - {repo['name']}: {repo['description']}")


@cli.command()
def stats():
    """Show database statistics"""
    click.echo("Fetching database statistics...")
    
    async def get_stats():
        from app.models.agent import Agent
        from app.models.repository import Repository
        from app.core.database import get_async_session
        
        async with get_async_session() as session:
            # Get repository count
            repo_count = await Repository.count(session)
            
            # Get agent count  
            agent_count = await Agent.count(session)
            
            # Get classification stats
            classified_count = await Agent.count_classified(session)
            
            click.echo(f"Repositories: {repo_count}")
            click.echo(f"Total agents: {agent_count}")
            click.echo(f"Classified agents: {classified_count}")
            click.echo(f"Classification rate: {classified_count/agent_count*100:.1f}%" if agent_count > 0 else "N/A")
    
    asyncio.run(get_stats())


if __name__ == "__main__":
    cli()