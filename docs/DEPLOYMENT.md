# Subagent Guild - Deployment Guide

This guide covers deploying the Subagent Guild system to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Manual Production Deployment](#manual-production-deployment)
4. [Configuration](#configuration)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements

**Minimum System Requirements:**
- OS: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB free space
- Network: Internet access for Git repository synchronization

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- Load balancer for high availability

### Required Dependencies

- Python 3.11+
- Git
- SQLite (included) or PostgreSQL (optional)
- Nginx (for reverse proxy)
- Docker & Docker Compose (for containerized deployment)

## Quick Start with Docker

The fastest way to deploy is using Docker Compose:

### 1. Clone Repository

```bash
git clone https://github.com/your-username/agent-guild.git
cd agent-guild
```

### 2. Configure Environment

```bash
cp .env.template .env
# Edit .env with your configuration
nano .env
```

**Required Environment Variables:**
```bash
CLAUDE_API_KEY=your_claude_api_key_here
DATABASE_URL=sqlite:///./data/db/agents.db
REPOSITORIES_PATH=/app/data/repositories
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f web
```

### 4. Initialize Data

```bash
# Access the running container
docker-compose exec web bash

# Run initial repository sync
python scripts/manage.py sync-repositories

# Start classification process
python scripts/manage.py classify-agents
```

The application will be available at `http://localhost:8000`.

## Manual Production Deployment

For production deployments on bare metal or VPS:

### 1. Run Deployment Script

```bash
# Download and run the deployment script
curl -sSL https://raw.githubusercontent.com/your-username/agent-guild/main/scripts/deploy.sh | bash
```

### 2. Manual Steps (Alternative)

If you prefer manual installation:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv git nginx certbot python3-certbot-nginx supervisor

# Create application directory
sudo mkdir -p /opt/agent-guild
sudo chown $USER:$USER /opt/agent-guild

# Clone repository
git clone https://github.com/your-username/agent-guild.git /opt/agent-guild
cd /opt/agent-guild

# Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt

# Configure environment
cp .env.template .env
# Edit .env with your settings

# Initialize database
python -c "import asyncio; from app.core.database import init_database; asyncio.run(init_database())"

# Create systemd services (see deploy.sh for service files)
sudo systemctl enable agent-guild agent-guild-scheduler
sudo systemctl start agent-guild agent-guild-scheduler

# Configure Nginx (see deploy.sh for configuration)
# Setup SSL with Certbot
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_API_KEY` | Yes | - | Your Claude API key |
| `DATABASE_URL` | No | `sqlite:///./data/db/agents.db` | Database connection string |
| `REPOSITORIES_PATH` | No | `./data/repositories` | Path for Git repositories |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `WORKERS` | No | `1` | Number of Gunicorn workers |
| `SYNC_INTERVAL_HOURS` | No | `24` | Repository sync interval |
| `MAX_DOWNLOAD_SIZE_MB` | No | `100` | Maximum download package size |

### Repository Configuration

Configure repositories to sync in `config/settings.py`:

```python
CONFIGURED_REPOSITORIES = [
    {
        "name": "anthropic/agent-examples",
        "url": "https://github.com/anthropic/agent-examples.git",
        "description": "Official Anthropic agent examples"
    },
    # Add your repositories here
]
```

### Database Options

**SQLite (Default):**
- Best for: Development, small-scale deployments
- Configuration: `DATABASE_URL=sqlite:///./data/db/agents.db`

**PostgreSQL (Recommended for Production):**
- Best for: Production, high-traffic deployments
- Configuration: `DATABASE_URL=postgresql://user:password@localhost/agentguild`

## Monitoring & Maintenance

### Health Checks

The application provides multiple health check endpoints:

- `/health` - Comprehensive health check
- `/health/ready` - Readiness probe (Kubernetes-compatible)
- `/health/live` - Liveness probe (Kubernetes-compatible)

### Monitoring Script

Run the built-in monitoring script:

```bash
# Check system status
./scripts/monitor.sh

# Add to cron for automated monitoring
crontab -e
# Add: */5 * * * * /opt/agent-guild/scripts/monitor.sh >> /opt/agent-guild/logs/monitor.log 2>&1
```

### Log Management

**Log Locations:**
- Application logs: `./logs/app.log`
- Scheduler logs: `./logs/scheduler.log`
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`

**Log Rotation:**
Log rotation is automatically configured for production deployments.

### Backup Strategy

**Database Backup:**
```bash
# SQLite backup
cp ./data/db/agents.db ./backups/agents_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL backup
pg_dump agentguild > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Repository Data:**
```bash
# Backup repository cache
tar -czf repositories_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./data/repositories/
```

### Updates

**Docker Deployment:**
```bash
docker-compose pull
docker-compose up -d
```

**Manual Deployment:**
```bash
cd /opt/agent-guild
git pull origin main
source venv/bin/activate
pip install -r requirements-prod.txt
sudo systemctl restart agent-guild agent-guild-scheduler
```

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check service status
sudo systemctl status agent-guild

# Check logs
sudo journalctl -u agent-guild -f

# Common fixes
sudo systemctl daemon-reload
sudo systemctl restart agent-guild
```

**Database Connection Issues:**
```bash
# Check database file permissions
ls -la ./data/db/

# Reset database
rm ./data/db/agents.db
python -c "import asyncio; from app.core.database import init_database; asyncio.run(init_database())"
```

**Repository Sync Failures:**
```bash
# Check Git access
git clone https://github.com/anthropic/agent-examples.git /tmp/test-clone

# Clear repository cache
rm -rf ./data/repositories/*

# Manual sync
python scripts/manage.py sync-repositories --verbose
```

**High Memory Usage:**
```bash
# Check memory usage
free -h
ps aux | grep python

# Reduce workers in production
# Edit .env: WORKERS=2
sudo systemctl restart agent-guild
```

### Performance Tuning

**For High Traffic:**
1. Increase worker processes: `WORKERS=4`
2. Use PostgreSQL instead of SQLite
3. Add Redis for caching
4. Use a CDN for static assets
5. Configure Nginx caching

**For Resource-Constrained Environments:**
1. Reduce sync frequency: `SYNC_INTERVAL_HOURS=48`
2. Limit classification batch size: `CLASSIFICATION_BATCH_SIZE=5`
3. Use single worker: `WORKERS=1`

## Security Considerations

### API Key Security

- Store Claude API key in environment variables, never in code
- Use file permissions to protect `.env` file: `chmod 600 .env`
- Rotate API keys regularly

### Network Security

- Use HTTPS in production (configured automatically with deployment script)
- Configure firewall to only allow necessary ports:
  ```bash
  sudo ufw allow 22    # SSH
  sudo ufw allow 80    # HTTP
  sudo ufw allow 443   # HTTPS
  sudo ufw enable
  ```

### Application Security

- Run application with non-root user
- Keep dependencies updated: `pip install --upgrade -r requirements-prod.txt`
- Monitor security advisories for dependencies
- Regular security scans: `pip-audit`

### Data Security

- Regular database backups
- Encrypt backups for off-site storage
- Monitor logs for suspicious activity
- Implement rate limiting for API endpoints

### Docker Security

- Use official base images
- Run containers as non-root user
- Keep Docker and base images updated
- Scan images for vulnerabilities

## Support

For issues and support:

1. Check logs for error messages
2. Review this troubleshooting guide
3. Search existing GitHub issues
4. Create a new issue with:
   - System information
   - Error logs
   - Steps to reproduce

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution guidelines.