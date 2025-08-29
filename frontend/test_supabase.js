// Simple test script to verify Supabase connection and data
const { createClient } = require('@supabase/supabase-js');

// Configuration - Read from environment variables
const supabaseUrl = process.env.SUPABASE_URL || 'https://ndysgbprcsbulnpgdpbm.supabase.co';
const supabaseKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

// Initialize Supabase client
const supabase = createClient(supabaseUrl, supabaseKey);

async function testConnection() {
    console.log('🔌 Testing Supabase connection...');
    
    try {
        // Test basic connection
        console.log('1. Testing basic connection...');
        const { data, error } = await supabase.from('repositories').select('count', { count: 'exact', head: true });
        
        if (error) {
            console.error('❌ Connection failed:', error);
            return;
        }
        
        console.log('✅ Connection successful!');
        
        // Test repositories data
        console.log('\n2. Testing repositories data...');
        const { data: repos, error: reposError } = await supabase
            .from('repositories')
            .select('*')
            .limit(5);
            
        if (reposError) {
            console.error('❌ Repositories query failed:', reposError);
        } else {
            console.log(`✅ Found ${repos.length} repositories:`);
            repos.forEach(repo => {
                console.log(`   - ${repo.name} (${repo.star_count} stars)`);
            });
        }
        
        // Test agents data
        console.log('\n3. Testing agents data...');
        const { data: agents, error: agentsError } = await supabase
            .from('agents')
            .select(`
                id,
                name,
                description,
                repository:repositories(name)
            `)
            .limit(5);
            
        if (agentsError) {
            console.error('❌ Agents query failed:', agentsError);
        } else {
            console.log(`✅ Found ${agents.length} agents:`);
            agents.forEach(agent => {
                console.log(`   - ${agent.name} (from ${agent.repository?.name || 'Unknown'})`);
            });
        }
        
        // Test classifications data
        console.log('\n4. Testing classifications data...');
        const { data: classifications, error: classificationsError } = await supabase
            .from('classifications')
            .select('lifecycle_phase, role_type')
            .limit(5);
            
        if (classificationsError) {
            console.error('❌ Classifications query failed:', classificationsError);
        } else {
            console.log(`✅ Found ${classifications.length} classifications:`);
            classifications.forEach(classification => {
                console.log(`   - ${classification.lifecycle_phase} / ${classification.role_type}`);
            });
        }
        
        // Test tech stacks data
        console.log('\n5. Testing tech stacks data...');
        const { data: techStacks, error: techStacksError } = await supabase
            .from('tech_stacks')
            .select('tag, category')
            .limit(5);
            
        if (techStacksError) {
            console.error('❌ Tech stacks query failed:', techStacksError);
        } else {
            console.log(`✅ Found ${techStacks.length} tech stack entries:`);
            techStacks.forEach(tech => {
                console.log(`   - ${tech.tag} (${tech.category})`);
            });
        }
        
        // Test full agent query with relationships
        console.log('\n6. Testing full agent query with relationships...');
        const { data: fullAgents, error: fullAgentsError } = await supabase
            .from('agents')
            .select(`
                *,
                repository:repositories(*),
                classifications(*),
                tech_stack(*)
            `)
            .limit(2);
            
        if (fullAgentsError) {
            console.error('❌ Full agent query failed:', fullAgentsError);
        } else {
            console.log(`✅ Full agent query successful!`);
            fullAgents.forEach(agent => {
                const classifications = agent.classifications || [];
                const techTags = agent.tech_stack || [];
                console.log(`   - ${agent.name}`);
                console.log(`     Classifications: ${classifications.length}`);
                console.log(`     Tech tags: ${techTags.length}`);
            });
        }
        
        console.log('\n🎉 All tests completed successfully!');
        console.log('\n📊 Summary:');
        console.log(`   - Repositories: ${repos?.length || 0}`);
        console.log(`   - Agents: ${agents?.length || 0}`);
        console.log(`   - Classifications: ${classifications?.length || 0}`);
        console.log(`   - Tech stack entries: ${techStacks?.length || 0}`);
        
    } catch (error) {
        console.error('❌ Test failed with exception:', error);
    }
}

// Run the test
testConnection();