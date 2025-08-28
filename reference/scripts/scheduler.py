#!/usr/bin/env python3
"""
Subagent Guild - Background Task Scheduler

Handles periodic tasks like repository synchronization and agent classification.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_async_session
from app.services.repository_sync import RepositorySyncService
from app.services.classification import ClassificationService
from config.settings import SYNC_INTERVAL_HOURS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Background task scheduler for agent guild operations"""
    
    def __init__(self):
        self.running = True
        self.repo_sync_service = RepositorySyncService()
        self.classification_service = ClassificationService()
        self.last_sync_time: Optional[datetime] = None
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def sync_repositories_task(self):
        """Periodic repository synchronization task"""
        try:
            logger.info("Starting repository synchronization...")
            
            async with get_async_session() as session:
                results = await self.repo_sync_service.sync_all_repositories(session)
                
                logger.info(f"Repository sync completed: {results}")
                self.last_sync_time = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Repository sync failed: {e}", exc_info=True)
    
    async def classify_agents_task(self):
        """Periodic agent classification task"""
        try:
            logger.info("Starting agent classification...")
            
            async with get_async_session() as session:
                results = await self.classification_service.classify_all_agents(session)
                
                logger.info(f"Agent classification completed: {results}")
                
        except Exception as e:
            logger.error(f"Agent classification failed: {e}", exc_info=True)
    
    async def health_check_task(self):
        """Periodic health check and cleanup"""
        try:
            # Log system health
            import psutil
            
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            logger.info(
                f"System health - CPU: {cpu_percent}%, "
                f"Memory: {memory.percent}%, "
                f"Disk: {disk.percent}%"
            )
            
            # Cleanup old temporary files
            import shutil
            import os
            from pathlib import Path
            
            temp_dir = Path("./data/temp")
            if temp_dir.exists():
                # Remove files older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_time:
                            file_path.unlink()
                            logger.debug(f"Cleaned up old temp file: {file_path}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
    
    def should_sync_repositories(self) -> bool:
        """Check if it's time for repository sync"""
        if self.last_sync_time is None:
            return True
        
        time_since_sync = datetime.utcnow() - self.last_sync_time
        return time_since_sync >= timedelta(hours=SYNC_INTERVAL_HOURS)
    
    async def run(self):
        """Main scheduler loop"""
        logger.info("Task scheduler starting...")
        self.setup_signal_handlers()
        
        # Initial sync on startup
        await self.sync_repositories_task()
        await self.classify_agents_task()
        
        while self.running:
            try:
                # Repository sync (every N hours)
                if self.should_sync_repositories():
                    await self.sync_repositories_task()
                    await self.classify_agents_task()
                
                # Health check (every 15 minutes)
                await self.health_check_task()
                
                # Sleep for 15 minutes
                for _ in range(900):  # 15 minutes in seconds
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Task scheduler stopped.")


async def main():
    """Main entry point"""
    scheduler = TaskScheduler()
    await scheduler.run()


if __name__ == "__main__":
    asyncio.run(main())