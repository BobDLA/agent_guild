-- Supabase Database Schema Setup
-- Run this in the Supabase SQL Editor

-- Create repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url VARCHAR(512) NOT NULL,
    description TEXT,
    star_count INTEGER DEFAULT 0,
    fork_count INTEGER DEFAULT 0,
    language VARCHAR(100),
    license VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    submodule_path VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_synced_at TIMESTAMP WITH TIME ZONE
);

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(512) NOT NULL,
    repository_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    system_prompt TEXT,
    yaml_metadata JSONB,
    content_hash VARCHAR(64),
    is_parsed BOOLEAN DEFAULT false,
    is_classified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    parsed_at TIMESTAMP WITH TIME ZONE
);

-- Create classifications table
CREATE TABLE IF NOT EXISTS classifications (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    lifecycle_phase VARCHAR(100) NOT NULL,
    role_type VARCHAR(100) NOT NULL,
    confidence_score FLOAT NOT NULL,
    is_ai_generated BOOLEAN DEFAULT true,
    is_reviewed BOOLEAN DEFAULT false,
    reviewed_by VARCHAR(100),
    review_notes VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    classified_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE
);

-- Create tech_stacks table
CREATE TABLE IF NOT EXISTS tech_stacks (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agents_repository_id ON agents(repository_id);
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
CREATE INDEX IF NOT EXISTS idx_classifications_agent_id ON classifications(agent_id);
CREATE INDEX IF NOT EXISTS idx_classifications_lifecycle_phase ON classifications(lifecycle_phase);
CREATE INDEX IF NOT EXISTS idx_classifications_role_type ON classifications(role_type);
CREATE INDEX IF NOT EXISTS idx_tech_stacks_agent_id ON tech_stacks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tech_stacks_tag ON tech_stacks(tag);

-- Enable Row Level Security
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE tech_stacks ENABLE ROW LEVEL SECURITY;

-- Create public read access policies
CREATE POLICY "Public read access" ON repositories FOR SELECT USING (true);
CREATE POLICY "Public read access" ON agents FOR SELECT USING (true);
CREATE POLICY "Public read access" ON classifications FOR SELECT USING (true);
CREATE POLICY "Public read access" ON tech_stacks FOR SELECT USING (true);

-- Create service role policies for inserts/updates (for the export script)
CREATE POLICY "Service role all access" ON repositories FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all access" ON agents FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all access" ON classifications FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all access" ON tech_stacks FOR ALL USING (auth.role() = 'service_role');

-- Add helpful comments
COMMENT ON TABLE repositories IS 'Git repositories containing Claude Code subagents';
COMMENT ON TABLE agents IS 'Individual Claude Code subagents extracted from repositories';
COMMENT ON TABLE classifications IS 'AI-generated categorizations of agents by lifecycle phase and role';
COMMENT ON TABLE tech_stacks IS 'Technology stack tags associated with agents';