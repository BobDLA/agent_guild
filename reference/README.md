# Subagent Guild - Quick Start

A centralized platform for discovering, evaluating, and managing Claude Code subagents from multiple repositories.

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/agent-guild.git
cd agent-guild

# Configure environment
cp .env.template .env
# Edit .env with your Claude API key and settings

# Start with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f web
```

Visit `http://localhost:8000` to access the application.

### Option 2: Manual Installation

```bash
# Run the automated deployment script
curl -sSL https://raw.githubusercontent.com/your-username/agent-guild/main/scripts/deploy.sh | bash

# Or install manually
git clone https://github.com/your-username/agent-guild.git
cd agent-guild

# Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your settings

# Initialize database
python -c "import asyncio; from app.core.database import init_database; asyncio.run(init_database())"

# Start the application
./scripts/start.sh
```

## 📋 Required Configuration

### Environment Variables

The minimum required configuration in your `.env` file:

```env
# Claude API Integration
CLAUDE_API_KEY=your_claude_api_key_here

# Database (SQLite by default)
DATABASE_URL=sqlite:///./data/db/agents.db

# Repository Storage
REPOSITORIES_PATH=./data/repositories

# Basic Settings
LOG_LEVEL=INFO
DEBUG=False
```

### Repository Sources

Configure which Git repositories to index in `config/settings.py`:

```python
CONFIGURED_REPOSITORIES = [
    {
        "name": "anthropic/agent-examples",
        "url": "https://github.com/anthropic/agent-examples.git",
        "description": "Official Anthropic agent examples"
    },
    {
        "name": "your-org/custom-agents",
        "url": "https://github.com/your-org/custom-agents.git", 
        "description": "Your custom agent collection"
    }
]
```

## 🔧 Management Commands

### Initialize Data

```bash
# Sync repositories and parse agents
python scripts/manage.py sync-repositories

# Classify agents using Claude
python scripts/manage.py classify-agents

# Validate parsed agents
python scripts/manage.py validate-agents
```

### Monitoring

```bash
# Check system health
curl http://localhost:8000/health

# Monitor with built-in script
./scripts/monitor.sh

# View logs
tail -f logs/app.log
```

## 🏗️ Architecture

### Components

- **FastAPI Backend**: Async web framework with SQLAlchemy ORM
- **Web Frontend**: Jinja2 templates with HTMX for interactivity
- **Agent Parser**: YAML frontmatter + Markdown content extraction
- **Classification System**: Claude API integration for automated categorization
- **Repository Sync**: Git submodule management for multi-repo aggregation
- **Download System**: ZIP package generation with custom selections

### Directory Structure

```
agent-guild/
├── app/                    # Application code
│   ├── api/               # API endpoints
│   ├── core/              # Database and config
│   ├── models/            # SQLAlchemy models  
│   ├── services/          # Business logic
│   └── web/               # Web interface
├── config/                # Configuration
├── data/                  # Runtime data
│   ├── db/               # Database files
│   ├── repositories/     # Git repository cache
│   └── temp/             # Temporary files
├── logs/                  # Application logs
├── scripts/               # Management scripts
├── static/                # Static assets
├── templates/             # Jinja2 templates
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🔒 Security

### Production Security Checklist

- [ ] Set strong `SECRET_KEY` in environment
- [ ] Use HTTPS in production (SSL/TLS certificates)
- [ ] Protect `.env` file permissions: `chmod 600 .env`
- [ ] Run application as non-root user
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Backup database regularly

### API Key Management

- Store Claude API key in environment variables only
- Rotate API keys regularly
- Monitor API usage and costs
- Use environment-specific keys (dev/staging/prod)

## 📊 Monitoring & Maintenance

### Health Checks

- `/health` - Comprehensive system health
- `/health/ready` - Kubernetes readiness probe  
- `/health/live` - Kubernetes liveness probe

### Log Management

Logs are automatically rotated and stored in:
- `logs/app.log` - Application logs
- `logs/error.log` - Error logs only
- `logs/access.log` - HTTP access logs
- `logs/scheduler.log` - Background task logs

### Performance Monitoring

Monitor key metrics:
- Response times
- Memory usage
- Disk space
- Database query performance
- Repository sync duration
- Classification processing time

### Backup Strategy

```bash
# Database backup
cp ./data/db/agents.db ./backups/agents_$(date +%Y%m%d_%H%M%S).db

# Repository cache backup  
tar -czf repositories_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./data/repositories/
```

## 🚀 Deployment Options

### Development
```bash
python main.py
```

### Production with Gunicorn
```bash
gunicorn -c gunicorn.conf.py main:app
```

### Docker Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Systemd Service (Linux)
```bash
sudo systemctl enable agent-guild
sudo systemctl start agent-guild
sudo systemctl status agent-guild
```

## 🧪 Testing

```bash
# Install test dependencies
pip install -r requirements.txt

# Run test suite
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test categories
pytest -m "not slow"           # Skip slow tests
pytest tests/unit/             # Unit tests only
pytest tests/integration/      # Integration tests only
pytest tests/e2e/              # End-to-end tests only
```

## 📚 Documentation

- [Deployment Guide](DEPLOYMENT.md) - Comprehensive deployment instructions
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)
- [Contributing Guide](CONTRIBUTING.md) - Development guidelines

## 🐛 Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs for errors
tail -f logs/app.log

# Verify dependencies
pip install -r requirements.txt

# Check database connection
python -c "from app.core.database import get_async_session; print('OK')"
```

**Repository sync failures:**
```bash
# Check Git access
git clone https://github.com/anthropic/agent-examples.git /tmp/test

# Clear cache and retry
rm -rf ./data/repositories/*
python scripts/manage.py sync-repositories --verbose
```

**Classification not working:**
```bash
# Verify Claude API key
echo $CLAUDE_API_KEY

# Test API connection
python -c "from app.services.classification import ClassificationService; print('OK')"
```

## 🤝 Support

- GitHub Issues: Report bugs and request features
- Documentation: Comprehensive guides and API docs
- Community: Join discussions and share agent discoveries

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.