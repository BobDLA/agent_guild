# Management Scripts

This directory contains CLI tools and management scripts for the Subagent Guild project.

## Scripts

### Database Management
- **`init_database.py`** - Initialize the database schema and tables
- **`force_reclassify.py`** - Force reclassification of all agents
- **`reclassify_with_cli.py`** - Reclassify agents using Claude CLI

### Synchronization
- **`sync_and_classify.py`** - Sync repositories and classify agents
- **`update_star_counts.py`** - Update repository star counts from GitHub

### Testing
- **`test_claude_cli.py`** - Test Claude CLI integration

## Usage

Run scripts from the project root directory:

```bash
# Initialize database
python management/init_database.py

# Sync and classify agents
python management/sync_and_classify.py

# Update star counts
python management/update_star_counts.py
```

## Requirements

- All scripts require the project dependencies to be installed
- Some scripts require environment variables (CLAUDE_API_KEY, GITHUB_TOKEN)
- Scripts should be run from the project root directory to maintain proper paths