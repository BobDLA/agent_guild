# Subagent Guild Configuration

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent.parent  # Project root
REPOSITORIES_DIR = BASE_DIR / "data" / "repositories"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/data/db/agents.db")

# GitHub API
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

# Claude API configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-3-sonnet-20240229"

# Repository configuration - public Claude Code subagent repositories
CONFIGURED_REPOSITORIES = [
    {
        "name": "wshobson/agents",
        "url": "https://github.com/wshobson/agents.git",
        "description": "Collection of Claude Code subagents"
    },
    {
        "name": "VoltAgent/awesome",
        "url": "https://github.com/VoltAgent/awesome.git", 
        "description": "Awesome Claude agents collection"
    },
    {
        "name": "iannuttall/claude-agents",
        "url": "https://github.com/iannuttall/claude-agents.git",
        "description": "Claude agent examples"
    },
    {
        "name": "davepoon/collection",
        "url": "https://github.com/davepoon/collection.git",
        "description": "Curated Claude agents"
    },
    {
        "name": "0xfurai/subagents",
        "url": "https://github.com/0xfurai/subagents.git",
        "description": "Specialized subagents"
    }
]

# Classification configuration
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.8
CLASSIFICATION_REVIEW_THRESHOLD = 0.6

# Web application settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Download limits
MAX_AGENTS_PER_DOWNLOAD = 50

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600  # 1 hour

# Lifecycle phases for classification
LIFECYCLE_PHASES = [
    "general",
    "concept", 
    "design",
    "development",
    "testing",
    "deployment", 
    "operations"
]

# Role types for classification
ROLE_TYPES = [
    "general",
    "product-manager",
    "system-architect", 
    "backend-developer",
    "frontend-developer",
    "performance-engineer",
    "devops-engineer",
    "qa-tester",
    "security-specialist",
    "data-engineer",
    "api-designer",
    "database-developer",
    "mobile-developer",
    "ui-ux-designer"
]

# Technology stack categories
TECH_CATEGORIES = [
    "general",
    "performance-optimization",
    "system-design", 
    "security",
    "testing",
    "deployment",
    "monitoring",
    "documentation"
]