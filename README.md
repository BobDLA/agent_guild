# Subagent Guild

A centralized platform for discovering, evaluating, and managing Claude Code subagents from multiple Git repositories. The Subagent Guild aggregates subagents from public repositories, classifies them using Claude API, and provides a web interface for browsing and downloading agent collections.

## 🌟 The Vision

The Subagent Guild was born from a simple observation: while Claude Code has unleashed incredible potential for developers through subagents, these powerful tools are scattered across countless repositories. There's no central place to discover, evaluate, and manage these agents efficiently.

Our mission is to create a thriving ecosystem where:
- **Developers** can easily discover agents that match their specific needs
- **Agent creators** can showcase their work to a wider audience
- **Teams** can curate collections of agents for their specific workflows
- **The community** can collaborate on improving and extending existing agents

## 🏗️ Architecture Overview

The Subagent Guild is built with a modern, scalable architecture:

### Backend (FastAPI)
- **REST API** with comprehensive endpoints for agents, repositories, and downloads
- **SQLite** database with async SQLAlchemy for optimal performance
- **Claude API integration** for intelligent agent classification
- **GitHub API integration** for repository metadata and star tracking

### Data Processing Pipeline
1. **Repository Synchronization** - Git submodule management across 5+ repositories
2. **Agent Discovery** - Scans for `.md` files with agent content and YAML frontmatter
3. **Content Parsing** - Extracts system prompts, metadata, and descriptions
4. **Intelligent Classification** - Uses Claude API to categorize by lifecycle phase and role
5. **Enrichment** - Adds tech stack tags and repository metadata
6. **Indexing** - Makes agents searchable through our web interface

### Frontend
- **Server-side rendering** with Jinja2 templates
- **HTMX** for dynamic interactions without heavy JavaScript
- **Tailwind CSS** for responsive, modern design
- **Mobile-first** approach for accessibility

## 🚀 Current Status

### 📊 Platform Statistics
- **5+ repositories** synchronized regularly
- **200+ agents** discovered and classified
- **27+ role types** categorized (from product managers to security specialists)
- **7 lifecycle phases** tracked (from concept to operations)

### 🤝 Partner Repositories

We're proud to collaborate with these amazing repositories:

- **[wshobson/agents](https://github.com/wshobson/agents)** - Collection of Claude Code subagents
- **[VoltAgent/awesome](https://github.com/VoltAgent/awesome)** - Awesome Claude agents collection  
- **[iannuttall/claude-agents](https://github.com/iannuttall/claude-agents)** - Claude agent examples
- **[davepoon/collection](https://github.com/davepoon/collection)** - Curated Claude agents
- **[0xfurai/subagents](https://github.com/0xfurai/subagents)** - Specialized subagents

### 🔍 Classification System

Our intelligent classification system categorizes agents into:

**Lifecycle Phases:**
- General Purpose
- Concept & Planning
- Design & Architecture  
- Development & Implementation
- Testing & Quality Assurance
- Deployment & Operations
- Monitoring & Maintenance

**Role Types (27 categories):**
- Product Management
- System Architecture
- Backend Development
- Frontend Development
- Performance Engineering
- DevOps & Infrastructure
- QA & Testing
- Security & Compliance
- Data Engineering
- API Design
- Database Development
- Mobile Development
- UI/UX Design
- And many more specialized roles...

## 🎯 Key Features

### For Developers
- **Search & Filter** - Find agents by technology, role, or lifecycle phase
- **Compare Agents** - Side-by-side comparison of similar agents
- **Download Collections** - Export curated agent sets for your team
- **Agent Ratings** - Community-driven quality assessment

### For Agent Creators
- **Showcase Your Work** - Get your agents discovered by thousands of developers
- **Analytics** - Track downloads, ratings, and usage statistics
- **Community Feedback** - Receive valuable input for improvements
- **Collaboration** - Connect with other agent creators

### For Teams
- **Team Collections** - Curate sets of agents for your specific workflows
- **Access Control** - Manage who can access and download collections
- **Usage Analytics** - Track which agents are most valuable to your team
- **Custom Integration** - API access for integrating with your tools

## 🌐 Access the Platform

**Live Demo**: [https://bobdla.github.io/agent_guild/](https://bobdla.github.io/agent_guild/)

**Local Development**:
- Backend API: `http://localhost:8000` (FastAPI)
- Frontend: `http://localhost:3000` (Development server)
- API Documentation: `http://localhost:8000/docs` (Swagger UI)

## 🙏 Acknowledgments

- **Anthropic** for creating Claude Code and enabling this ecosystem
- **Our partner repositories** for sharing their amazing agents
- **The Claude Code community** for feedback and contributions
- **Open source contributors** who make projects like this possible

---

**Built with ❤️ by the Subagent Guild team**

*Join us in building the future of agent discovery and collaboration!*