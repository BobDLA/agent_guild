# GitHub Actions + Supabase Deployment Design

## Overview

This design outlines the deployment of the Subagent Guild application as a simplified frontend-only solution using GitHub Pages and Supabase. The approach separates data processing (local) from data serving (cloud), where repository synchronization and Claude API classification are handled locally, and the pre-built database is synced to Supabase for frontend consumption.

## Architecture

### Current vs Target Architecture

```mermaid
graph TB
subgraph "Local Data Processing"
A1[Local FastAPI App] --> B1[SQLite Database]
A1 --> C1[GitHub Repos]
A1 --> D1[Claude API]
B1 --> E1[Database Export]
end

subgraph "Cloud Frontend"
E1 --> F2[Supabase PostgreSQL]
F2 --> G2[GitHub Pages Frontend]
G2 --> H2[Static Site/SPA]
end
```

### Deployment Strategy

The application uses a hybrid local-cloud deployment model:

1. **Local Data Processing**: Repository sync and Claude classification run locally
2. **Database Sync**: Local SQLite data exported and synced to Supabase PostgreSQL
3. **Frontend Deployment**: Static frontend deployed to GitHub Pages
4. **Data Access**: Frontend queries Supabase directly via REST API
5. **Updates**: Manual database sync when local data changes

## Technology Stack Migration

### Local Data Processing (Unchanged)

**Current Local Setup:**
```python
# Keep existing local configuration
DATABASE_URL = "sqlite+aiosqlite:///data/db/agents.db"
CLAUDE_API_KEY = "your-claude-api-key"
```

**Local Processing Components:**
- FastAPI application (existing)
- SQLite database (existing)
- Repository sync scripts (existing)
- Claude API classification (existing)
- All existing management scripts

### Frontend Technology Migration

**From FastAPI + Jinja2 Templates:**
```python
# Current server-side rendering
@app.get("/agents")
async def agents_page(request: Request):
    # Server-side data fetching
    agents = await get_agents_from_db()
    return templates.TemplateResponse(
        "agents.html", 
        {"request": request, "agents": agents}
    )
```

**To Static Frontend + Supabase API:**
```javascript
// Client-side data fetching
async function loadAgents() {
    const response = await fetch(
        `${SUPABASE_URL}/rest/v1/agents`,
        {
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            }
        }
    );
    const agents = await response.json();
    renderAgents(agents);
}
```

### Data Sync Strategy

**SQLite to Supabase Export Script:**
```python
# scripts/sync_to_supabase.py
import sqlite3
import asyncpg
import asyncio
from config.settings import DATABASE_URL

async def export_to_supabase():
    # Read from local SQLite
    sqlite_conn = sqlite3.connect('data/db/agents.db')
    
    # Connect to Supabase PostgreSQL
    pg_conn = await asyncpg.connect(SUPABASE_DATABASE_URL)
    
    # Export each table
    await export_table(sqlite_conn, pg_conn, 'repositories')
    await export_table(sqlite_conn, pg_conn, 'agents')
    await export_table(sqlite_conn, pg_conn, 'classifications')
    
    await pg_conn.close()
    sqlite_conn.close()
```

**Frontend Build Process:**
```bash
# package.json scripts
{
  "scripts": {
    "build": "webpack --mode production",
    "deploy": "npm run build && gh-pages -d dist"
  }
}
```

### Simplified GitHub Deployment

```mermaid
graph TD
A[Local Development] --> B[Database Export]
B --> C[Supabase Sync]
A --> D[Frontend Build]
D --> E[GitHub Pages Deploy]
E --> F[Static Frontend]
F --> G[Supabase API]
```

**Deployment Workflow:**

1. **Frontend Deployment** (`deploy-frontend.yml`)
   - Triggers: Push to main branch
   - Jobs: Build static frontend → Deploy to GitHub Pages
   - Duration: ~2-5 minutes
   - Output: Static site served from GitHub Pages

2. **Database Sync** (Manual Process)
   - Local: Export SQLite data to SQL/JSON
   - Supabase: Import data via dashboard or CLI
   - Frequency: As needed when local data updates
   - Output: Updated Supabase database

### Supabase Database Schema

**Table Migrations:**

```sql
-- Agents table (PostgreSQL optimized)
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_id INTEGER REFERENCES repositories(id),
    file_path VARCHAR(500),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_repository_id ON agents(repository_id);
CREATE INDEX idx_agents_metadata ON agents USING GIN(metadata);
```

**Configuration Management:**
- Supabase project setup with free tier (500MB storage, 2GB bandwidth)
- Row Level Security (RLS) policies for data protection
- Database connection pooling optimization
- Backup configuration within free tier limits

## Data Flow Architecture

### Simplified Data Flow

```mermaid
sequenceDiagram
    participant Local as Local Machine
    participant SQLite as SQLite DB
    participant Supabase as Supabase DB
    participant Frontend as GitHub Pages
    participant User as User Browser

    Local->>SQLite: Repository sync & classification
    Local->>SQLite: Export data
    Local->>Supabase: Sync exported data
    Local->>Frontend: Deploy frontend updates
    User->>Frontend: Browse application
    Frontend->>Supabase: Query data via REST API
    Supabase->>Frontend: Return JSON responses
```

**Processing Stages:**

1. **Local Data Processing**
   - Repository synchronization using existing scripts
   - Agent parsing and Claude classification
   - All processing handled by current local system

2. **Database Export & Sync**
   - Export SQLite data to PostgreSQL-compatible format
   - Manual or scripted sync to Supabase
   - Preserve data relationships and integrity

3. **Frontend Deployment**
   - Static site generation for GitHub Pages
   - SPA (Single Page Application) for dynamic features
   - Direct API calls to Supabase from browser

## API Design

### Frontend API Integration

Direct integration with Supabase REST API:

```javascript
// Frontend queries Supabase directly
const supabaseUrl = 'https://[project-id].supabase.co'
const supabaseKey = '[anon-public-key]'

// Get all agents
fetch(`${supabaseUrl}/rest/v1/agents`, {
  headers: {
    'apikey': supabaseKey,
    'Authorization': `Bearer ${supabaseKey}`
  }
})

// Search and filter
fetch(`${supabaseUrl}/rest/v1/agents?name=like.*${query}*`, {
  headers: {
    'apikey': supabaseKey,
    'Authorization': `Bearer ${supabaseKey}`
  }
})
```

### Supabase Auto-Generated API

Supabase automatically provides REST endpoints for all tables:

- `GET /rest/v1/agents` - List all agents
- `GET /rest/v1/repositories` - List repositories  
- `GET /rest/v1/classifications` - Get classifications
- Full query support with filters, sorting, pagination

## Configuration Management

### Local Environment (Unchanged)

**Keep existing local configuration:**
```bash
# .env (local development)
DATABASE_URL=sqlite+aiosqlite:///data/db/agents.db
CLAUDE_API_KEY=your-claude-api-key
GITHUB_TOKEN=your-github-token
DEBUG=true
HOST=127.0.0.1
PORT=8000
```

### Frontend Environment Variables

**GitHub Pages Environment:**
```javascript
// config/frontend.js
const config = {
    SUPABASE_URL: 'https://[project-id].supabase.co',
    SUPABASE_ANON_KEY: '[public-anon-key]',
    API_BASE_URL: 'https://[project-id].supabase.co/rest/v1'
};
```

**GitHub Repository Secrets (for build process):**
```yaml
# Only needed for automated deployment
SUPABASE_URL: https://[project-id].supabase.co
SUPABASE_ANON_KEY: [public-anon-key]
```

### Supabase Configuration

**Database Setup:**
```sql
-- Enable Row Level Security
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE classifications ENABLE ROW LEVEL SECURITY;

-- Public read access policy
CREATE POLICY "Public read access" ON agents FOR SELECT USING (true);
CREATE POLICY "Public read access" ON repositories FOR SELECT USING (true);
CREATE POLICY "Public read access" ON classifications FOR SELECT USING (true);
```

### Frontend Dependencies

**New Frontend Dependencies:**
```json
{
  "devDependencies": {
    "webpack": "^5.88.0",
    "webpack-cli": "^5.1.0",
    "html-webpack-plugin": "^5.5.0",
    "css-loader": "^6.8.0",
    "style-loader": "^3.3.0",
    "gh-pages": "^6.0.0"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.38.0"
  }
}
```

**No Changes to Python Dependencies:**
```txt
# Keep existing requirements.txt for local development
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
# ... all existing dependencies unchanged
```

**GitHub Pages Limits (Free Tier):**
- 1GB repository storage
- 100GB bandwidth/month
- Custom domains supported
- HTTPS automatically enabled

**Supabase Limits (Free Tier):**
- 500MB database storage
- 2GB bandwidth/month
- 50,000 monthly active users
- Unlimited API requests

**Optimization Strategies:**
- Minimal GitHub Actions usage (frontend deployment only)
- Efficient frontend bundle size
- Optimized Supabase queries
- Client-side caching strategies

## Security Considerations

### Access Control

**Supabase Security:**
```sql
-- Row Level Security policies
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON agents
    FOR SELECT USING (true);

CREATE POLICY "Service role write access" ON agents
    FOR ALL USING (auth.role() = 'service_role');
```

**GitHub Actions Security:**
- Secrets management for API keys
- Principle of least privilege for permissions
- Secure handling of database credentials
- Audit logging for all operations

### Data Protection

- HTTPS enforcement for all connections
- Database connection encryption
- API key rotation procedures
- Backup and recovery procedures

## Implementation Roadmap

### Phase 1: Database Setup (Week 1)

1. **Supabase Project Setup**
   - Create Supabase project
   - Configure PostgreSQL schema matching SQLite structure
   - Set up Row Level Security policies
   - Test API endpoints

2. **Data Export Script**
   - Create SQLite to PostgreSQL export script
   - Handle data type conversions
   - Preserve relationships and constraints
   - Test data integrity

### Phase 2: Frontend Development (Week 2)

1. **Static Site Creation**
   - Convert FastAPI templates to static HTML/JS
   - Implement Supabase JavaScript client
   - Add client-side routing (if needed)
   - Style and optimize for performance

2. **API Integration**
   - Implement agent listing and search
   - Add filtering and pagination
   - Handle download functionality
   - Test all frontend features

### Phase 3: GitHub Pages Deployment (Week 3)

1. **Deployment Setup**
   - Configure GitHub Pages
   - Set up build workflow
   - Add environment variables for Supabase
   - Test deployment pipeline

2. **Performance Optimization**
   - Optimize bundle size
   - Implement caching strategies
   - Add loading states
   - Test on different devices

### Phase 4: Data Sync Process (Week 4)

1. **Sync Automation**
   - Create data sync script
   - Schedule local processing
   - Automate Supabase updates
   - Document update procedures

2. **Testing & Launch**
   - End-to-end testing
   - Performance validation
   - Documentation updates
   - Go live with monitoring

## Cost Analysis

### Current Costs
- Local hosting: $0 (development only)
- Cloud hosting: ~$10-50/month (if deployed)

### Target Costs
- GitHub Actions: $0 (within free tier limits)
- Supabase: $0 (within free tier limits)
- Total: **$0/month**

**Free Tier Sustainability:**
- Estimated monthly usage: <1,000 Action minutes
- Database size: <100MB initially
- Bandwidth: <500MB/month
- High confidence in staying within limits

## Risk Assessment

### Technical Risks

**Medium Risk: Action Execution Limits**
- Mitigation: Optimize workflows, implement incremental processing
- Monitoring: Track execution time and resource usage

**Low Risk: Database Storage Limits**
- Mitigation: Data archiving, efficient schema design
- Monitoring: Database size tracking

**Low Risk: API Rate Limits**
- Mitigation: Implement proper rate limiting and caching
- Monitoring: API usage tracking

### Operational Risks

**Low Risk: Service Availability**
- Both GitHub and Supabase have high availability
- Backup procedures for critical data
- Fallback plans for service outages

**Medium Risk: Configuration Complexity**
- Comprehensive documentation
- Automated testing of configurations
- Version control for all settings

## Monitoring & Maintenance

### Performance Monitoring

```yaml
# .github/workflows/monitoring.yml
- name: Monitor Database Size
  run: |
    # Check Supabase database size
    # Alert if approaching limits
    
- name: Monitor Action Usage
  run: |
    # Track GitHub Actions minutes
    # Optimize if approaching limits
```

### Maintenance Procedures

1. **Weekly Reviews**
   - Check resource usage
   - Review error logs
   - Validate data quality

2. **Monthly Optimization**
   - Database cleanup
   - Workflow optimization
   - Performance tuning

3. **Quarterly Updates**
   - Dependency updates
   - Security reviews
   - Feature enhancements

## Code Reusability Analysis

### Existing Code That Can Be 100% Reused (No Changes)

**Local Data Processing Layer (完全保留)**
```
app/
├── models/           # 100% reusable - all SQLAlchemy models
│   ├── agent.py      # ✅ Keep as-is
│   ├── repository.py # ✅ Keep as-is
│   ├── classification.py # ✅ Keep as-is
│   └── tech_stack.py # ✅ Keep as-is
├── services/         # 100% reusable - all business logic
│   ├── agent_parser.py     # ✅ Keep as-is
│   ├── classification.py   # ✅ Keep as-is
│   ├── discovery.py        # ✅ Keep as-is
│   └── repository_sync.py  # ✅ Keep as-is
├── core/
│   └── database.py   # ✅ Keep as-is
config/
└── settings.py       # ✅ Keep as-is
management/           # 100% reusable - all CLI scripts
├── sync_and_classify.py # ✅ Keep as-is
├── init_database.py     # ✅ Keep as-is
└── force_reclassify.py  # ✅ Keep as-is
requirements.txt      # ✅ Keep as-is
main.py              # ✅ Keep as-is
manage.py            # ✅ Keep as-is
```

**Reusable Assets (可重用资源)**
- All CSS styles from `templates/base.html` (24KB of styling)
- All JavaScript functions for UI interactions
- All Tailwind CSS classes and custom styles
- Database schema and relationships
- Business logic and data processing algorithms
- Claude API integration and classification logic

### Frontend Code That Can Be Heavily Reused (轻微修改)

**Templates Structure (85% reusable)**
```
templates/
├── base.html         # 85% reusable - HTML structure + CSS
├── pages/            # 70% reusable - convert to static HTML
│   ├── homepage.html     # ✅ Convert Jinja2 → Static HTML
│   ├── agents.html       # ✅ Convert Jinja2 → JavaScript
│   ├── agent_detail.html # ✅ Convert Jinja2 → JavaScript  
│   ├── comparison.html   # ✅ Convert Jinja2 → JavaScript
│   └── download.html     # ✅ Convert Jinja2 → JavaScript
└── partials/         # 60% reusable - convert to JS components
    ├── agent_cards.html  # ✅ Convert to JavaScript function
    └── selection_summary.html # ✅ Convert to JavaScript function
```

### Code That Needs New Implementation (需要新建)

**New Frontend Code (新增约2000行)**
```
frontend/                    # 🆕 New directory
├── src/
│   ├── js/
│   │   ├── app.js          # 🆕 ~500 lines - main application
│   │   ├── supabase.js     # 🆕 ~200 lines - database client
│   │   ├── components/     # 🆕 ~800 lines total
│   │   │   ├── AgentCard.js
│   │   │   ├── SearchFilter.js
│   │   │   ├── AgentDetail.js
│   │   │   └── DownloadManager.js
│   │   └── utils/
│   │       └── helpers.js  # 🆕 ~200 lines
│   ├── css/
│   │   └── styles.css      # ✅ Copy from base.html + minor additions
│   └── html/
│       └── index.html      # 🆕 ~300 lines - SPA shell
├── package.json            # 🆕 ~50 lines
├── webpack.config.js       # 🆕 ~100 lines
└── .github/workflows/
    └── deploy.yml          # 🆕 ~50 lines
```

**Database Export Script (新增约300行)**
```
scripts/
└── export_to_supabase.py   # 🆕 ~300 lines - data sync script
```

### **建议的项目结构策略 (Recommended Project Structure)**

**推荐方案: 使用分支 (Branch Approach) ✅**

```bash
# 创建新分支进行云端迁移
git checkout -b feature/github-supabase-deployment

# 项目结构将变成:
project-root/
├── app/                    # 保持不变 - 本地开发用
├── config/                 # 保持不变
├── management/             # 保持不变
├── templates/              # 保持不变 - 本地开发用
├── frontend/               # 🆕 新增 - 云端前端
│   ├── src/
│   ├── dist/               # 构建输出
│   ├── package.json
│   └── webpack.config.js
├── scripts/
│   └── export_to_supabase.py  # 🆕 新增
├── .github/workflows/      # 🆕 新增
│   └── deploy-frontend.yml
└── README-cloud.md         # 🆕 新增 - 云端部署文档
```

**分支方案的优势:**

1. **代码历史完整保留**
   - 所有提交历史和开发记录保持连续
   - 可以轻松对比本地版本和云端版本的差异
   - 便于未来维护和bug追踪

2. **灵活的开发模式**
   ```bash
   # 继续本地开发
   git checkout main
   python main.py  # 本地版本继续工作
   
   # 开发云端版本
   git checkout feature/github-supabase-deployment
   cd frontend && npm run dev  # 云端版本开发
   ```

3. **渐进式迁移**
   - 可以随时切换回稳定的本地版本
   - 云端功能可以逐个迁移和测试
   - 降低迁移风险

4. **共享资源利用**
   - 数据库导出脚本可以访问现有的models和services
   - 可以重用现有的CSS和JavaScript代码
   - 配置文件可以共享基础设置

**vs. 新项目方案的劣势:**

❌ **新项目 (New Repository)**
```bash
# 问题较多的方案
git clone current-project new-cloud-project
```
- 失去代码历史连续性
- 需要重复配置git设置和secrets
- 代码同步变得复杂
- 难以合并改进回原项目
- 维护两套独立的代码库

**实施步骤:**

```bash
# 1. 创建功能分支
git checkout -b feature/github-supabase-deployment

# 2. 添加云端相关文件
mkdir frontend
mkdir .github/workflows

# 3. 开发云端功能
# ... 按设计文档实施 ...

# 4. 测试云端部署
git push origin feature/github-supabase-deployment

# 5. 部署成功后，可选择:
# 5a. 保持分支独立 (推荐)
# 5b. 合并到main分支
```

**长期维护策略:**

```bash
# 方案A: 双分支维护 (推荐)
main分支                    # 本地开发版本
cloud分支                   # 云端部署版本

# 方案B: 统一分支 (高级)
main分支                    # 包含本地和云端两套代码
├── 本地开发: python main.py
└── 云端构建: npm run build
```

**推荐选择: 方案A - 双分支维护**
- 保持代码职责清晰
- 本地开发不受云端代码影响
- 云端部署独立且稳定
- 便于将来根据需要选择主要方向

### **备份和比较验证策略 (Backup & Comparison Strategy)**

**实施前完整备份 (Pre-Migration Backup)**

```bash
# 1. 创建当前状态的备份标签
git tag -a v1.0-local-baseline -m "Baseline before cloud migration"
git push origin v1.0-local-baseline

# 2. 创建完整的功能文档快照
cd /Users/twomonkeys/work/qoder/agent_quild2

# 3. 记录当前系统状态
echo "=== Current System Baseline ===" > migration-baseline.md
echo "Date: $(date)" >> migration-baseline.md
echo "Database: $(ls -la data/db/)" >> migration-baseline.md
echo "Agents Count: $(sqlite3 data/db/agents.db 'SELECT COUNT(*) FROM agents;')" >> migration-baseline.md
echo "Repositories: $(sqlite3 data/db/agents.db 'SELECT name FROM repositories WHERE is_active=1;')" >> migration-baseline.md

# 4. 备份关键配置和数据
mkdir migration-backup
cp -r data/ migration-backup/
cp -r templates/ migration-backup/
cp -r static/ migration-backup/
cp config/settings.py migration-backup/
cp requirements.txt migration-backup/
cp .env migration-backup/
```

**功能对比检查清单 (Feature Comparison Checklist)**

```markdown
# Migration Verification Checklist

## 📊 Data Integrity
- [ ] Agent count matches (Local vs Supabase)
- [ ] Repository count matches
- [ ] Classifications preserved
- [ ] Tech stack data complete
- [ ] Download selections functional

## 🎨 Frontend Features
- [ ] Homepage displays correctly
- [ ] Agent listing with pagination
- [ ] Search functionality
- [ ] Filtering by lifecycle/role/tech
- [ ] Agent detail view
- [ ] Comparison feature
- [ ] Download selection
- [ ] Repository listing

## 🔧 User Interactions
- [ ] Agent card hover effects
- [ ] Search autocomplete
- [ ] Filter dropdowns
- [ ] Add to team/compare buttons
- [ ] Download package generation
- [ ] Responsive design (mobile/tablet)

## 📱 UI/UX Consistency
- [ ] Color scheme matches
- [ ] Typography consistent
- [ ] Button styles preserved
- [ ] Loading states functional
- [ ] Error handling works
- [ ] Notifications display
```

**自动化比较脚本 (Automated Comparison Script)**

```python
# scripts/compare_versions.py
import sqlite3
import requests
import json
from datetime import datetime

def compare_data_integrity():
    """Compare local SQLite with Supabase data"""
    
    # Local data
    local_conn = sqlite3.connect('data/db/agents.db')
    local_agents = local_conn.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    local_repos = local_conn.execute('SELECT COUNT(*) FROM repositories WHERE is_active=1').fetchone()[0]
    
    # Supabase data
    supabase_url = "https://[project-id].supabase.co/rest/v1"
    headers = {
        'apikey': '[anon-key]',
        'Authorization': 'Bearer [anon-key]'
    }
    
    agents_resp = requests.get(f"{supabase_url}/agents", headers=headers)
    repos_resp = requests.get(f"{supabase_url}/repositories?is_active=eq.true", headers=headers)
    
    supabase_agents = len(agents_resp.json())
    supabase_repos = len(repos_resp.json())
    
    # Generate comparison report
    report = {
        'timestamp': datetime.now().isoformat(),
        'local': {
            'agents': local_agents,
            'repositories': local_repos
        },
        'supabase': {
            'agents': supabase_agents,
            'repositories': supabase_repos
        },
        'match': {
            'agents': local_agents == supabase_agents,
            'repositories': local_repos == supabase_repos
        }
    }
    
    with open('migration-comparison.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Data Comparison Report:")
    print(f"Agents: Local({local_agents}) vs Supabase({supabase_agents}) - {'✅' if report['match']['agents'] else '❌'}")
    print(f"Repos: Local({local_repos}) vs Supabase({supabase_repos}) - {'✅' if report['match']['repositories'] else '❌'}")

def compare_ui_screenshots():
    """Generate screenshots for visual comparison"""
    # Using Playwright or similar for automated screenshots
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        # Local version screenshots
        page = browser.new_page()
        page.goto('http://127.0.0.1:8000')
        page.screenshot(path='migration-backup/local-homepage.png')
        page.goto('http://127.0.0.1:8000/agents')
        page.screenshot(path='migration-backup/local-agents.png')
        
        # Cloud version screenshots
        page.goto('https://[your-username].github.io/[repo-name]')
        page.screenshot(path='migration-backup/cloud-homepage.png')
        page.screenshot(path='migration-backup/cloud-agents.png')
        
        browser.close()

if __name__ == '__main__':
    compare_data_integrity()
    # compare_ui_screenshots()  # Uncomment when both versions are running
```

**性能基准测试 (Performance Baseline)**

```bash
# scripts/performance_baseline.sh
#!/bin/bash

echo "=== Performance Baseline Test ==="
echo "Date: $(date)" > performance-baseline.txt

# Local version performance
echo "\n--- Local Version ---" >> performance-baseline.txt
echo "Startup time:" >> performance-baseline.txt
time python main.py &
PID=$!
sleep 5
kill $PID

# API response times
echo "\nAPI Response Times (Local):" >> performance-baseline.txt
for endpoint in "/agents" "/repositories" "/health"; do
    echo "$endpoint: $(curl -w '%{time_total}' -s -o /dev/null http://127.0.0.1:8000$endpoint)s" >> performance-baseline.txt
done

# Database query performance
echo "\nDatabase Queries:" >> performance-baseline.txt
echo "Agent count query: $(time sqlite3 data/db/agents.db 'SELECT COUNT(*) FROM agents;')" >> performance-baseline.txt

echo "Baseline recorded in performance-baseline.txt"
```

**迁移验证工作流 (Migration Verification Workflow)**

```bash
# Step 1: Pre-migration backup
git checkout main
./scripts/create_baseline.sh

# Step 2: Create migration branch
git checkout -b feature/github-supabase-deployment

# Step 3: Implement cloud version
# ... follow design document ...

# Step 4: Data verification
python scripts/compare_versions.py

# Step 5: Functional testing
# Manual testing using checklist above

# Step 6: Performance comparison
./scripts/performance_comparison.sh

# Step 7: Generate migration report
echo "Migration completed: $(date)" > migration-report.md
echo "Data integrity: $(cat migration-comparison.json)" >> migration-report.md
echo "Performance impact: $(cat performance-comparison.txt)" >> migration-report.md
```

**回滚策略 (Rollback Strategy)**

```bash
# If migration issues occur:
# 1. Quick rollback to local version
git checkout main
python main.py  # Local system immediately available

# 2. Restore from backup if needed
cp -r migration-backup/data/ ./
cp migration-backup/.env ./

# 3. Database restore if corrupted
cp migration-backup/data/db/agents.db data/db/

# 4. Clean migration branch for retry
git branch -D feature/github-supabase-deployment
git checkout -b feature/github-supabase-deployment
```

**定期同步验证 (Regular Sync Verification)**

```bash
# Weekly verification script
# cron: 0 0 * * 0 /path/to/weekly_verify.sh

#!/bin/bash
# weekly_verify.sh
cd /Users/twomonkeys/work/qoder/agent_quild2

# Update local data
python manage.py sync_repos
python manage.py classify_agents

# Sync to Supabase
python scripts/export_to_supabase.py

# Verify sync
python scripts/compare_versions.py

# Send report (optional)
echo "Weekly sync completed: $(date)" | mail -s "Subagent Guild Sync Report" your-email@domain.com
```
└── export_to_supabase.py   # 🆕 ~300 lines - data sync script
```

### Detailed Conversion Requirements

**1. Template to JavaScript Conversion (主要工作量)**

**Current Jinja2 Template:**
```html
<!-- templates/pages/agents.html -->
{% for agent in agents %}
<div class="agent-card">
    <h3>{{ agent.name }}</h3>
    <p>{{ agent.description }}</p>
    <span class="lifecycle-{{ agent.classification.lifecycle_phase }}">
        {{ agent.classification.lifecycle_phase }}
    </span>
</div>
{% endfor %}
```

**Convert to JavaScript:**
```javascript
// frontend/src/js/components/AgentCard.js
function renderAgentCard(agent) {
    return `
        <div class="agent-card">
            <h3>${agent.name}</h3>
            <p>${agent.description}</p>
            <span class="lifecycle-${agent.classification?.lifecycle_phase}">
                ${agent.classification?.lifecycle_phase}
            </span>
        </div>
    `;
}
```

**2. Server-Side Logic to Client-Side API Calls**

**Current FastAPI Endpoint:**
```python
# app/api/agents.py
@router.get("/agents")
async def get_agents(request: Request):
    agents = await get_agents_from_db()
    return templates.TemplateResponse("agents.html", {"agents": agents})
```

**Convert to Frontend API Call:**
```javascript
// frontend/src/js/app.js
async function loadAgents() {
    const { data } = await supabase
        .from('agents')
        .select('*, classification:classifications(*), repository:repositories(*)');
    renderAgents(data);
}
```

**3. HTMX to Vanilla JavaScript**

**Current HTMX:**
```html
<div hx-get="/api/agents" hx-trigger="load" hx-target="#agent-list">
```

**Convert to JavaScript:**
```javascript
document.addEventListener('DOMContentLoaded', async () => {
    await loadAgents();
});
```

### Migration Effort Estimation

**Time Investment (开发时间估算)**
```
数据库设置和导出脚本:     1-2 天
Supabase 项目配置:       0.5 天  
前端代码转换:           3-4 天
  - JavaScript 组件:     2 天
  - API 集成:           1 天
  - 样式调整:           0.5 天
  - 测试和调试:         0.5 天
GitHub Pages 部署:      0.5 天
测试和优化:            1 天
---
总计:                  6-8 天
```

**Code Lines Impact (代码行数影响)**
```
保持不变:    ~8,000 行 (85%)
轻微修改:    ~1,000 行 (10%) 
新增代码:    ~1,200 行 (5%)
删除代码:    ~200 行 (FastAPI routes)
---
总体变化:    15% 代码需要修改或新增
```

### Risk Assessment for Migration

**低风险 (Low Risk)**
- 数据模型和业务逻辑完全保留
- 本地开发环境不受影响
- 可以逐步迁移，保持现有系统运行
- 所有现有功能都能在新架构中实现

**中等风险 (Medium Risk)**
- 前端交互逻辑需要重写 (从 HTMX 到 JavaScript)
- 需要学习 Supabase API 集成
- 首次部署可能需要调试

**建议的迁移策略 (Migration Strategy)**
1. **并行开发**: 保持现有系统运行，新建 `frontend/` 目录
2. **功能对等**: 确保新前端具备所有现有功能
3. **渐进部署**: 先部署静态版本，再添加动态功能
4. **回滚计划**: 保留现有代码作为备份

### Database Export Script

```python
# scripts/export_to_supabase.py
import sqlite3
import json
import asyncio
import asyncpg
from datetime import datetime

async def export_sqlite_to_supabase():
    """Export local SQLite data to Supabase PostgreSQL"""
    
    # Local SQLite connection
    sqlite_conn = sqlite3.connect('/Users/twomonkeys/work/qoder/agent_quild2/data/db/agents.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    # Supabase PostgreSQL connection
    supabase_url = "postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres"
    pg_conn = await asyncpg.connect(supabase_url)
    
    try:
        # Export repositories
        print("Exporting repositories...")
        repos = sqlite_conn.execute("SELECT * FROM repositories").fetchall()
        for repo in repos:
            await pg_conn.execute(
                """
                INSERT INTO repositories (id, name, url, description, star_count, last_sync, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    star_count = EXCLUDED.star_count,
                    last_sync = EXCLUDED.last_sync,
                    is_active = EXCLUDED.is_active
                """,
                repo['id'], repo['name'], repo['url'], repo['description'],
                repo['star_count'], repo['last_sync'], repo['is_active']
            )
        
        # Export agents
        print("Exporting agents...")
        agents = sqlite_conn.execute("SELECT * FROM agents").fetchall()
        for agent in agents:
            await pg_conn.execute(
                """
                INSERT INTO agents (id, name, description, repository_id, file_path, content, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                """,
                agent['id'], agent['name'], agent['description'], agent['repository_id'],
                agent['file_path'], agent['content'], agent['metadata'],
                agent['created_at'], agent['updated_at']
            )
        
        print(f"Exported {len(repos)} repositories and {len(agents)} agents")
        
    finally:
        await pg_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    asyncio.run(export_sqlite_to_supabase())
```

### Frontend Application Structure

```javascript
// frontend/src/app.js
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://[project-id].supabase.co'
const supabaseKey = '[anon-public-key]'
const supabase = createClient(supabaseUrl, supabaseKey)

class AgentApp {
    constructor() {
        this.agents = []
        this.repositories = []
        this.filters = {
            search: '',
            lifecycle: 'all',
            role: 'all',
            repository: 'all'
        }
        this.init()
    }

    async init() {
        await this.loadData()
        this.renderApp()
        this.setupEventListeners()
    }

    async loadData() {
        try {
            // Load agents with repository info
            const { data: agents, error: agentsError } = await supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(name, description),
                    classification:classifications(*)
                `)
            
            if (agentsError) throw agentsError
            this.agents = agents

            // Load repositories
            const { data: repositories, error: reposError } = await supabase
                .from('repositories')
                .select('*')
                .eq('is_active', true)
            
            if (reposError) throw reposError
            this.repositories = repositories

        } catch (error) {
            console.error('Error loading data:', error)
            this.showError('Failed to load data')
        }
    }

    async searchAgents(query) {
        try {
            const { data, error } = await supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(name),
                    classification:classifications(*)
                `)
                .or(`name.ilike.%${query}%,description.ilike.%${query}%`)
            
            if (error) throw error
            return data
        } catch (error) {
            console.error('Search error:', error)
            return []
        }
    }

    renderAgents(agents = this.agents) {
        const container = document.getElementById('agents-container')
        container.innerHTML = agents.map(agent => `
            <div class="agent-card" data-id="${agent.id}">
                <h3>${agent.name}</h3>
                <p>${agent.description}</p>
                <div class="agent-meta">
                    <span class="repository">${agent.repository?.name}</span>
                    <span class="lifecycle">${agent.classification?.lifecycle_phase || 'general'}</span>
                    <span class="role">${agent.classification?.role_type || 'general'}</span>
                </div>
                <button onclick="app.selectAgent(${agent.id})" class="select-btn">
                    Select for Download
                </button>
            </div>
        `).join('')
    }

    selectAgent(agentId) {
        // Handle agent selection for download
        const selectedAgents = JSON.parse(localStorage.getItem('selectedAgents') || '[]')
        if (!selectedAgents.includes(agentId)) {
            selectedAgents.push(agentId)
            localStorage.setItem('selectedAgents', JSON.stringify(selectedAgents))
            this.updateDownloadButton()
        }
    }

    updateDownloadButton() {
        const selectedAgents = JSON.parse(localStorage.getItem('selectedAgents') || '[]')
        const downloadBtn = document.getElementById('download-btn')
        downloadBtn.textContent = `Download ${selectedAgents.length} Agents`
        downloadBtn.disabled = selectedAgents.length === 0
    }
}

// Initialize app
const app = new AgentApp()
window.app = app
```

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy-frontend.yml
name: Deploy Frontend to GitHub Pages

on:
  push:
    branches: [ main ]
    paths: [ 'frontend/**' ]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: 'frontend/package-lock.json'

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Build frontend
      run: |
        cd frontend
        npm run build
      env:
        SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
        SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./frontend/dist
        cname: your-domain.com  # Optional: custom domain
```

This design provides a comprehensive roadmap for migrating the Subagent Guild application to a completely free, cloud-based infrastructure using GitHub Actions and Supabase. The solution maintains all current functionality while eliminating hosting costs and improving scalability.