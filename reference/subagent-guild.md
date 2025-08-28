# Subagent Guild - System Design Document

## Overview

The Subagent Guild is a centralized web service designed to discover, evaluate, and manage Claude Code subagents from multiple public Git repositories. The system provides an intelligent marketplace-style platform that aggregates, categorizes, and simplifies the evaluation and integration of Claude Code subagents for developers.

### Key Features
- Multi-repository subagent aggregation via Git submodules
- Intelligent classification using Claude local prompting
- Two-row layout browser for intuitive navigation
- Side-by-side agent comparison functionality
- One-click package download and integration
- GitHub repository metadata enrichment

### Technology Classification
This is a **Full-Stack Application** - combining backend data processing with frontend user interface components.

## Architecture

### System Architecture Overview

```mermaid
graph TB
    subgraph "External Sources"
        GR1[GitHub Repo 1<br/>wshobson/agents]
        GR2[GitHub Repo 2<br/>VoltAgent/awesome]
        GR3[GitHub Repo 3<br/>iannuttall/claude-agents]
        GR4[GitHub Repo 4<br/>davepoon/collection]
        GR5[GitHub Repo 5<br/>0xfurai/subagents]
    end
    
    subgraph "Data Processing Layer"
        SM[Git Submodules<br/>Management]
        AP[Agent Parser<br/>YAML + Markdown]
        CS[Classification System<br/>Claude Local Prompting]
        DE[Data Enrichment<br/>GitHub API]
    end
    
    subgraph "Core System"
        DB[(SQLite/PostgreSQL<br/>Database)]
        API[FastAPI<br/>Web Service]
        WEB[Web Interface<br/>Jinja2 + HTMX]
    end
    
    subgraph "User Interface"
        HOME[Homepage<br/>Two-Row Layout]
        LIST[Agent Lists<br/>Search & Filter]
        COMP[Comparison View<br/>Side-by-side]
        DOWN[Download<br/>ZIP Package]
    end
    
    GR1 --> SM
    GR2 --> SM
    GR3 --> SM
    GR4 --> SM
    GR5 --> SM
    
    SM --> AP
    AP --> CS
    CS --> DE
    DE --> DB
    
    DB --> API
    API --> WEB
    WEB --> HOME
    WEB --> LIST
    WEB --> COMP
    WEB --> DOWN
```

### Script-Driven Monolith Pattern

The system follows separation between online services and offline processing:

#### Online Services (FastAPI)
- Serve database content to users
- API endpoints for agent discovery
- Web interface rendering
- Real-time search and filtering
- Package generation and download

#### Offline Processing (Python Scripts)
- Data ingestion and processing
- Git repository synchronization
- Agent parsing and classification
- External data enrichment
- Database updates

## Frontend Architecture

### Component Hierarchy

```mermaid
graph TD
    APP[App Shell]
    
    APP --> HEADER[Header Component]
    APP --> MAIN[Main Content]
    APP --> FOOTER[Footer Component]
    
    MAIN --> HOME[Homepage Component]
    MAIN --> LIST[Agent List Component]
    MAIN --> DETAIL[Agent Detail Component]
    MAIN --> COMP[Comparison Component]
    
    HOME --> TWOLAYOUT[Two-Row Layout]
    TWOLAYOUT --> MGMT[Management Roles Row]
    TWOLAYOUT --> TIMELINE[Timeline Row]
    
    LIST --> SEARCH[Search Bar]
    LIST --> FILTERS[Filter Panel]
    LIST --> CARDS[Agent Cards Grid]
    LIST --> PAGINATION[Pagination]
    
    COMP --> PANELS[Comparison Panels]
    COMP --> EXPORT[Export Controls]
    
    CARDS --> CARD[Agent Card]
    CARD --> SELECT[Selection Checkbox]
    CARD --> ACTIONS[Quick Actions]
```

### State Management

Hybrid approach combining server-side rendering with client-side interactivity:

#### Server-Side State (Jinja2 Templates)
- Initial page rendering
- SEO-friendly content
- Form handling and validation

#### Client-Side State (HTMX + Vanilla JS)
- Dynamic filtering and search
- Agent selection management
- Comparison panel updates
- Download preparation

### User Experience Design

#### Progressive Filter Interface

```mermaid
graph LR
    subgraph "Step 1: Intent"
        A1[Search: 'React performance']
    end
    
    subgraph "Step 2: Context" 
        B1[Complexity: Beginner]
        B2[Project Phase: Development]
        B3[Tech Stack: React + Node.js]
    end
    
    subgraph "Step 3: Results"
        C1[Ranked Agents]
        C2[Live Preview]
        C3[Quick Compare]
    end
    
    A1 --> B1
    B1 --> C1
```

#### Agent Discovery Flow

```mermaid
flowchart LR
    A["👥 Browse Guild Halls"] --> B["👁️ Meet Partners"]
    B --> C["🤝 Check Compatibility"]
    C --> D["💼 Build Your Team"]
    D --> E["📦 Take Partners Home"]
    
    A1["🔍 Search by Need"] --> B
    A2["🎯 Browse Specialties"] --> B
    A3["✨ Get Recommendations"] --> B
```

## Backend Architecture

### Data Models & Database Design

```mermaid
erDiagram
    Repository ||--o{ Agent : contains
    Agent ||--o{ Classification : has
    Agent ||--o{ TechStack : tagged_with
    Agent ||--o{ DownloadSelection : selected_in
    
    Repository {
        id INTEGER PK
        name VARCHAR
        url VARCHAR
        description TEXT
        star_count INTEGER
        last_updated DATETIME
        submodule_path VARCHAR
    }
    
    Agent {
        id INTEGER PK
        name VARCHAR
        description TEXT
        file_path VARCHAR
        repository_id INTEGER FK
        system_prompt TEXT
        yaml_metadata JSON
        parsed_at DATETIME
    }
    
    Classification {
        id INTEGER PK
        agent_id INTEGER FK
        lifecycle_phase VARCHAR
        role_type VARCHAR
        confidence_score FLOAT
        classified_at DATETIME
    }
    
    TechStack {
        id INTEGER PK
        agent_id INTEGER FK
        tag VARCHAR
        category VARCHAR
    }
    
    DownloadSelection {
        id INTEGER PK
        session_id VARCHAR
        agent_id INTEGER FK
        selected_at DATETIME
    }
```

### Classification Hierarchy

```mermaid
graph TD
    LP[Lifecycle Phases<br/>7 Categories]
    RT[Role Types<br/>27 Categories]
    TS[Tech Stack<br/>Technology Tags]
    
    LP --> LP1[Across All Lifecycle]
    LP --> LP2[Concept Planning]
    LP --> LP3[Design Architecture]
    LP --> LP4[Development Implementation]
    LP --> LP5[Testing QA]
    LP --> LP6[Deployment Release]
    LP --> LP7[Operations Optimization]
    
    RT --> RT1[Product Manager]
    RT --> RT2[System Architect]
    RT --> RT3[Backend Developer]
    RT --> RT4[Performance Engineer]
    RT --> RT5[...]
    
    TS --> TS1[General]
    TS --> TS2[Performance Optimization]
    TS --> TS3[System Design]
    TS --> TS4[Go, Python, React...]
```

### API Endpoints Reference

#### Agent Discovery

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/agents` | Retrieve filtered list of agents |
| GET | `/api/agents/{agent_id}/related` | Get related agents for discovery |
| GET | `/api/agents/popular` | Get most downloaded agents |

#### Comparison and Download

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/agents/compare` | Compare multiple agents side-by-side |
| POST | `/api/download/package` | Generate ZIP package of selected agents |

#### Repository Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/repositories` | List all configured repositories |
| POST | `/api/repositories/sync` | Trigger repository synchronization |

## Business Logic Layer

### Agent Discovery Workflow

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant FilterEngine
    participant DB
    
    User->>WebUI: Select lifecycle phase
    WebUI->>FilterEngine: Apply phase filter
    FilterEngine->>DB: Query with distribution balancing
    DB-->>FilterEngine: Return balanced result set
    FilterEngine-->>WebUI: Prioritize diverse agents
    WebUI-->>User: Display varied agent options
    
    User->>WebUI: Refine with role filter
    WebUI->>FilterEngine: Apply combined filters
    FilterEngine->>DB: Multi-dimensional query
    DB-->>FilterEngine: Return targeted results
    FilterEngine-->>WebUI: Show relevant agents
    WebUI-->>User: Present focused selection
```

### Classification Processing Workflow

```mermaid
flowchart TD
    START[Start Classification Process]
    PARSE[Parse Agent Files]
    EXTRACT[Extract Metadata & Content]
    CLAUDE[Claude Local Prompting]
    CLASSIFY[Generate Classifications]
    CONFIDENCE{Confidence > 80%?}
    AUTO[Auto-Accept]
    MANUAL[Manual Review]
    FALLBACK[Assign General Category]
    STORE[Store in Database]
    END[Classification Complete]
    
    START --> PARSE
    PARSE --> EXTRACT
    EXTRACT --> CLAUDE
    CLAUDE --> CLASSIFY
    CLASSIFY --> CONFIDENCE
    CONFIDENCE -->|Yes| AUTO
    CONFIDENCE -->|No, but > 60%| MANUAL
    CONFIDENCE -->|No, < 60%| FALLBACK
    AUTO --> STORE
    MANUAL --> STORE
    FALLBACK --> STORE
    STORE --> END
    
    MANUAL -->|Admin Override| STORE
```

### Package Generation Workflow

```mermaid
flowchart TD
    SELECT[User Selects Agents]
    VALIDATE[Validate Selection]
    CREATE[Create Temp Directory]
    COPY[Copy Agent Files]
    README[Generate README.md]
    ZIP[Create ZIP Package]
    CLEANUP[Cleanup Temp Files]
    DOWNLOAD[Serve Download]
    
    SELECT --> VALIDATE
    VALIDATE --> CREATE
    CREATE --> COPY
    COPY --> README
    README --> ZIP
    ZIP --> CLEANUP
    CLEANUP --> DOWNLOAD
```

## Data Flow Architecture

### Repository Synchronization Flow

```mermaid
sequenceDiagram
    participant Admin
    participant CLI
    participant GitSubmodules
    participant Parser
    participant Claude
    participant DB
    
    Admin->>CLI: python manage.py sync-repos
    CLI->>GitSubmodules: git submodule update --remote
    GitSubmodules->>Parser: Scan for .md files
    Parser->>Parser: Extract YAML frontmatter
    Parser->>Claude: Classify agents locally
    Claude-->>Parser: Return classifications
    Parser->>DB: Store agents & classifications
    DB-->>Admin: Sync complete notification
```

### User Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant Database
    
    User->>Browser: Visit homepage
    Browser->>FastAPI: GET /
    FastAPI->>Database: Load featured agents
    Database-->>FastAPI: Return agent data
    FastAPI-->>Browser: Render homepage
    Browser-->>User: Display two-row layout
    
    User->>Browser: Click "Backend Developer"
    Browser->>FastAPI: GET /agents?role=backend-developer
    FastAPI->>Database: Query filtered agents
    Database-->>FastAPI: Return results
    FastAPI-->>Browser: Update page content (HTMX)
    Browser-->>User: Show filtered agents
    
    User->>Browser: Select agents for comparison
    Browser->>FastAPI: POST /api/agents/compare
    FastAPI->>Database: Fetch agent details
    Database-->>FastAPI: Return full agent data
    FastAPI-->>Browser: Render comparison view
    Browser-->>User: Display side-by-side comparison
```

## Testing Strategy

### Unit Testing
- **Parser Components**: YAML extraction, content validation
- **Classification Logic**: Claude integration, confidence scoring  
- **API Endpoints**: Request/response handling, input validation
- **Business Logic**: Filtering, sorting, comparison algorithms

### Integration Testing
- **Database Operations**: CRUD operations, complex queries
- **External APIs**: GitHub API integration, rate limiting
- **File System**: Git submodule operations, file parsing

### End-to-End Testing  
- **User Workflows**: Complete discovery and download flows
- **Browser Compatibility**: HTMX interactions, responsive design
- **Performance**: Load times, search responsiveness