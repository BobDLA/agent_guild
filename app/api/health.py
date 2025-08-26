# Health Check Endpoint

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
from datetime import datetime
import os
import psutil

from app.core.database import get_async_session

router = APIRouter()


@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database connectivity check
    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy", 
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # File system checks
    try:
        # Check if data directories exist and are writable
        data_dir = "./data"
        repo_dir = "./data/repositories"
        
        for directory in [data_dir, repo_dir]:
            if os.path.exists(directory) and os.access(directory, os.W_OK):
                continue
            else:
                raise Exception(f"Directory {directory} not accessible")
        
        health_status["checks"]["filesystem"] = {
            "status": "healthy",
            "message": "File system access OK"
        }
    except Exception as e:
        health_status["checks"]["filesystem"] = {
            "status": "unhealthy",
            "message": f"File system check failed: {str(e)}"
        }
        overall_healthy = False
    
    # System resource checks
    try:
        # Memory check
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        memory_healthy = memory.percent < 90
        disk_healthy = disk.percent < 90
        
        if memory_healthy and disk_healthy:
            health_status["checks"]["resources"] = {
                "status": "healthy",
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "message": "Resource usage normal"
            }
        else:
            health_status["checks"]["resources"] = {
                "status": "warning",
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "message": "High resource usage detected"
            }
            if memory.percent > 95 or disk.percent > 95:
                overall_healthy = False
    except Exception as e:
        health_status["checks"]["resources"] = {
            "status": "unhealthy",
            "message": f"Resource check failed: {str(e)}"
        }
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        return JSONResponse(
            status_code=503,
            content=health_status
        )
    
    # Check for warnings
    warning_count = sum(1 for check in health_status["checks"].values() 
                       if check["status"] == "warning")
    if warning_count > 0:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Quick database check
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    return {"status": "alive"}