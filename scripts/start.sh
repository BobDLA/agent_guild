#!/bin/bash

# Subagent Guild - Production Startup Script

set -e

# Configuration
APP_DIR="/opt/agent-guild"
LOG_DIR="$APP_DIR/logs"
DATA_DIR="$APP_DIR/data"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Change to application directory
cd $APP_DIR

# Source environment
if [ -f ".env" ]; then
    source .env
else
    error ".env file not found!"
    exit 1
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    error "Virtual environment not found!"
    exit 1
fi

# Create necessary directories
log "Creating application directories..."
mkdir -p $LOG_DIR $DATA_DIR/repositories $DATA_DIR/db $DATA_DIR/temp

# Check dependencies
log "Checking dependencies..."
python -c "import fastapi, sqlalchemy, anthropic" || {
    error "Missing dependencies. Run: pip install -r requirements-prod.txt"
    exit 1
}

# Initialize database if needed
if [ ! -f "$DATA_DIR/db/agents.db" ]; then
    log "Initializing database..."
    python -c "
import asyncio
from app.core.database import init_database
asyncio.run(init_database())
" || {
        error "Database initialization failed!"
        exit 1
    }
else
    log "Database already exists, skipping initialization"
fi

# Run migrations (if any)
log "Checking for database migrations..."
# Add migration logic here if using Alembic

# Validate configuration
log "Validating configuration..."
if [ -z "$CLAUDE_API_KEY" ]; then
    warn "CLAUDE_API_KEY not set - classification will not work"
fi

# Pre-flight checks
log "Running pre-flight checks..."

# Check disk space
DISK_USAGE=$(df -h $DATA_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    warn "Disk usage is ${DISK_USAGE}% - consider cleaning up"
fi

# Check memory
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 80 ]; then
    warn "Memory usage is ${MEMORY_USAGE}% - monitor closely"
fi

# Test database connection
log "Testing database connection..."
python -c "
import asyncio
from app.core.database import get_async_session
from sqlalchemy import text

async def test_db():
    try:
        async with get_async_session() as session:
            await session.execute(text('SELECT 1'))
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        exit(1)

asyncio.run(test_db())
" || exit 1

# Start the application
log "Starting Subagent Guild..."

if [ "$1" = "development" ]; then
    log "Starting in development mode..."
    python main.py
elif [ "$1" = "gunicorn" ]; then
    log "Starting with Gunicorn..."
    exec gunicorn -c gunicorn.conf.py main:app
else
    log "Starting with Uvicorn (default)..."
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers ${WORKERS:-1} \
        --access-log \
        --log-config logging.json
fi