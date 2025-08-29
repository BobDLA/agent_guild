# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Subagent Guild** - a centralized platform for discovering, evaluating, and managing Claude Code subagents from multiple Git repositories. The application aggregates subagents from public repositories, classifies them using Claude API, and provides a web interface for browsing and downloading agent collections.

## Development Commands

### Local Development
```bash
# Start development server
python main.py

# Initialize database
python management/init_database.py

# Run management commands
python management/sync_and_classify.py      # Sync repos and classify agents
python management/force_reclassify.py       # Force reclassification of all agents
python management/update_star_counts.py    # Update repository star counts

# Test Claude API integration
python management/test_claude_cli.py
```

### Database Operations
```bash
# Sync repositories and parse agents
python -c "from app.services.repository_sync import RepositorySyncService; asyncio.run(RepositorySyncService().sync_all_repositories())"

# Parse all agents from repositories
python -c "from app.services.agent_parser import AgentParserService; asyncio.run(AgentParserService().parse_all_agents())"

# Classify agents using Claude API
python -c "from app.services.classification import ClassificationService; asyncio.run(ClassificationService().classify_all_agents())"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m e2e               # End-to-end tests only
pytest -k "test_agent"      # Tests matching name pattern

# Run specific test file
pytest tests/unit/test_agent_model.py
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Production Deployment
```bash
# Using startup script
./scripts/start.sh                # Default production startup
./scripts/start.sh development    # Development mode
./scripts/start.sh gunicorn       # Production with Gunicorn

# Using Docker
docker-compose up -d
```

## Architecture Overview

### Core Components

**FastAPI Backend** (`reference/app/`)
- `api/` - REST API endpoints (agents, repositories, downloads, health)
- `models/` - SQLAlchemy data models with relationships
- `services/` - Business logic (parsing, classification, discovery)
- `core/` - Database configuration and utilities
- `web/` - Web page rendering with Jinja2 templates

**Data Processing Pipeline**
1. **Repository Sync** (`services/repository_sync.py`) - Git submodule management
2. **Agent Parsing** (`services/agent_parser.py`) - YAML frontmatter + Markdown extraction
3. **Classification** (`services/classification.py`) - Claude API integration
4. **Database Storage** - SQLite with async SQLAlchemy

**Frontend Architecture**
- Server-side rendering with Jinja2 templates
- HTMX for dynamic interactions
- Tailwind CSS for styling
- Responsive design with mobile support

### Key Data Models

**Agent** (`models/agent.py`)
- Central entity representing Claude Code subagents
- Relationships: Repository, Classification, TechStack, DownloadSelection
- Advanced search/filtering with lifecycle phases and role types

**Repository** (`models/repository.py`)
- Git repositories containing subagent collections
- Star count tracking and metadata enrichment

**Classification** (`models/classification.py`)
- Claude API-generated categorizations
- Lifecycle phases (concept → operations) and role types (27 categories)
- Confidence scoring and automated review

### Configuration Management

**Environment Variables** (`.env`)
```env
# Required
CLAUDE_API_KEY=your_claude_api_key_here
DATABASE_URL=sqlite+aiosqlite:///data/db/agents.db
GITHUB_TOKEN=your_github_token_here

# Optional
DEBUG=false
HOST=127.0.0.1
PORT=8000
```

**Repository Configuration** (`config/settings.py`)
The system syncs from 5 configured repositories:
- `wshobson/agents` - Collection of Claude Code subagents
- `VoltAgent/awesome` - Awesome Claude agents collection
- `iannuttall/claude-agents` - Claude agent examples
- `davepoon/collection` - Curated Claude agents
- `0xfurai/subagents` - Specialized subagents

## Development Workflow

### Adding New Features

1. **Database Changes**: Update models in `app/models/`, then run migrations
2. **API Endpoints**: Add to `app/api/` with proper error handling
3. **Business Logic**: Implement in `app/services/`
4. **Frontend**: Update templates in `templates/` or add new pages in `app/web/`
5. **Tests**: Add unit, integration, and e2e tests in `tests/`

### Working with External APIs

**Claude API Integration**:
- Use `ClassificationService` for agent categorization
- API key in `CLAUDE_API_KEY` environment variable
- Handles rate limiting and error recovery

**GitHub API Integration**:
- Used for repository metadata (star counts, descriptions)
- Token in `GITHUB_TOKEN` environment variable
- Automatic rate limiting and caching

### Agent Processing Pipeline

The system processes agents through these stages:

1. **Repository Synchronization**: Git submodule updates
2. **File Discovery**: Scans for `.md` files with agent content
3. **Content Parsing**: Extracts YAML frontmatter and system prompts
4. **Classification**: Claude API categorizes by lifecycle phase and role
5. **Enrichment**: Adds tech stack tags and repository metadata
6. **Indexing**: Makes searchable through web interface

## Testing Strategy

### Test Structure
```
tests/
├── conftest.py           # Test configuration and fixtures
├── unit/                 # Unit tests (isolated components)
│   ├── test_agent_model.py
│   └── test_agent_parser.py
├── integration/          # Integration tests (API endpoints)
│   └── test_api_endpoints.py
└── e2e/                  # End-to-end tests (user workflows)
    └── test_user_workflows.py
```

### Key Test Patterns
- **Unit Tests**: Mock external dependencies, test individual methods
- **Integration Tests**: Test API endpoints with test database
- **E2E Tests**: Full user workflows from browser interaction
- **Database Tests**: Use pytest-asyncio with async session fixtures

## Performance Considerations

### Database Optimization
- Use async SQLAlchemy for non-blocking database operations
- Proper indexing on frequently queried fields
- Pagination for large result sets
- Query optimization with selectinload for relationships

### API Rate Limiting
- Built-in rate limiting for GitHub API (requests per hour)
- Claude API usage monitoring and cost tracking
- Caching for repository metadata

### Memory Management
- Streaming processing for large agent files
- Connection pooling for database connections
- Proper cleanup of temporary files and resources

## Security Considerations

### API Key Management
- Store keys in environment variables only
- Never commit API keys to version control
- Use different keys for development and production

### Input Validation
- All user inputs validated at API boundaries
- SQL injection prevention through SQLAlchemy ORM
- File path sanitization for repository operations

### Data Protection
- HTTPS enforcement for all API calls
- Secure storage of sensitive configuration
- Regular backup of database and repository data

## Deployment Notes

### Production Setup
- Use Gunicorn for production serving
- Configure proper logging with rotation
- Set up monitoring for health endpoints
- Regular database backups

### Scaling Considerations
- Database: Can migrate to PostgreSQL for larger deployments
- File Storage: External storage for agent files and downloads
- Caching: Redis for frequently accessed data
- CDN: For static assets in production

## Common Issues and Solutions

### Database Connection Issues
```bash
# Check database file exists
ls -la data/db/agents.db

# Test database connection
python -c "from app.core.database import get_async_session; asyncio.run(get_async_session())"
```

### Repository Sync Failures
```bash
# Check Git access
git ls-remote https://github.com/wshobson/agents.git

# Clear repository cache and retry
rm -rf data/repositories/*
python management/sync_and_classify.py
```

### Claude API Issues
```bash
# Test API key
python -c "import os; print('API key set:', bool(os.getenv('CLAUDE_API_KEY')))"

# Check API connectivity
python management/test_claude_cli.py
```

### Template Rendering Issues
```bash
# Check template syntax
python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); env.get_template('base.html')"
```

## Future Development Plans

The project has a planned migration to GitHub Pages + Supabase architecture (see `github-supabase-deployment.md`). This will involve:
- Converting Jinja2 templates to static frontend with JavaScript
- Exporting SQLite data to Supabase PostgreSQL
- Deploying frontend to GitHub Pages
- Maintaining local data processing pipeline


## Don't merge the working branch to main. till user required to do it.
## please visit the  frontend only  at :3000.  Please use play wright to debug the issue Please capture a picture when you   solve it。 But don't ocr the picture or try to under stand the picture. You don't have the ability to do that. 
## Please refer to the referece design. 