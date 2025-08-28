// Subagent Guild Application
// Complete rewrite to match original FastAPI + HTMX functionality

class SubagentGuildApp {
    constructor() {
        // Configuration - will be updated with actual Supabase values
        this.supabaseUrl = 'https://ndysgbprcsbulnpgdpbm.supabase.co';
        this.supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5keXNnYnByY3NidWxucGdkcGJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MDA0NjAsImV4cCI6MjA3MTk3NjQ2MH0.7TvoErb20c0lf9p_cIBDHLRmUlzbHXUTP2YKyHrTwX8';
        
        // Initialize Supabase client
        this.supabase = window.supabase.createClient(this.supabaseUrl, this.supabaseKey);
        
        // State management
        this.agents = [];
        this.repositories = [];
        this.selectedAgents = new Set();
        this.comparisonList = new Set();
        this.filters = {
            search: '',
            lifecycle: '',
            role: '',
            repository: '',
            tech_stack: []
        };
        this.pagination = {
            page: 1,
            limit: 12,
            total: 0,
            totalPages: 0
        };
        
        // Initialize the application
        this.init();
    }
    
    async init() {
        console.log('🏰 Initializing Subagent Guild...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadStats();
        await this.loadRepositories();
        
        // Initialize counters
        this.updateCounters();
        
        // Hide loading spinner
        this.hideLoading();
        
        console.log('✅ Subagent Guild initialized successfully');
    }
    
    setupEventListeners() {
        // Navigation
        document.addEventListener('click', (e) => {
            if (e.target.matches('a[href^="/"]')) {
                e.preventDefault();
                const path = e.target.getAttribute('href');
                this.handleNavigation(path);
            }
        });
        
        // Search and filter functionality
        const searchInput = document.getElementById('quick-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.filters.search = searchInput.value;
                this.loadAgents();
            }, 500));
        }
        
        // Lifecycle filter
        const lifecycleFilter = document.getElementById('lifecycle-filter');
        if (lifecycleFilter) {
            lifecycleFilter.addEventListener('change', () => {
                this.filters.lifecycle = lifecycleFilter.value;
                this.loadAgents();
            });
        }
        
        // Role filter
        const roleFilter = document.getElementById('role-filter');
        if (roleFilter) {
            roleFilter.addEventListener('change', () => {
                this.filters.role = roleFilter.value;
                this.loadAgents();
            });
        }
        
        // Search button
        const searchBtn = document.getElementById('search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                this.loadAgents();
            });
        }
        
        // Reset filters button
        const resetBtn = document.getElementById('reset-filters-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetFilters();
            });
        }
        
        // Sort and limit selectors
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                this.loadAgents();
            });
        }
        
        const limitSelect = document.getElementById('limit-select');
        if (limitSelect) {
            limitSelect.addEventListener('change', () => {
                this.pagination.limit = parseInt(limitSelect.value);
                this.pagination.page = 1;
                this.loadAgents();
            });
        }
        
        // Compare and download buttons
        const compareBtn = document.getElementById('compare-btn');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => {
                this.navigateToCompare();
            });
        }
        
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.navigateToDownload();
            });
        }
        
        // Modal close button
        const closeModal = document.getElementById('close-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                this.closeAgentModal();
            });
        }
        
        // Click outside modal to close
        const modal = document.getElementById('agent-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeAgentModal();
                }
            });
        }
    }
    
    async loadStats() {
        try {
            // Load agents count
            const { count: agentsCount, error: agentsError } = await this.supabase
                .from('agents')
                .select('*', { count: 'exact', head: true });
            
            if (agentsError) throw agentsError;
            
            // Load repositories count
            const { count: reposCount, error: reposError } = await this.supabase
                .from('repositories')
                .select('*', { count: 'exact', head: true });
            
            if (reposError) throw reposError;
            
            // Load classification rate
            const { data: classifiedAgents, error: classifiedError } = await this.supabase
                .from('agents')
                .select('id', { count: 'exact' })
                .eq('is_classified', true);
            
            if (classifiedError) throw classifiedError;
            
            // Calculate classification rate
            const classificationRate = agentsCount > 0 ? Math.round((classifiedAgents.length / agentsCount) * 100) : 0;
            
            // Load lifecycle phases
            const { data: lifecycles, error: lifecycleError } = await this.supabase
                .from('classifications')
                .select('lifecycle_phase');
            
            if (lifecycleError) throw lifecycleError;
            
            const uniqueLifecycles = [...new Set(lifecycles.map(l => l.lifecycle_phase))];
            
            // Update UI
            this.updateElement('total-agents', agentsCount || 0);
            this.updateElement('total-repositories', reposCount || 0);
            this.updateElement('classification-rate', `${classificationRate}%`);
            this.updateElement('lifecycle-count', uniqueLifecycles.length);
            
            // Load phase-specific counts
            await this.loadPhaseCounts();
            
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showToast('Error loading statistics', 'error');
        }
    }
    
    async loadPhaseCounts() {
        try {
            const phases = ['development', 'testing', 'deployment', 'operations'];
            
            for (const phase of phases) {
                const { data: agents, error } = await this.supabase
                    .from('classifications')
                    .select('agent_id', { count: 'exact' })
                    .eq('lifecycle_phase', phase);
                
                if (error) throw error;
                
                const elementId = `${phase.replace('-', '')}-phase-count`;
                this.updateElement(elementId, agents?.length || 0);
            }
        } catch (error) {
            console.error('Error loading phase counts:', error);
        }
    }
    
    async loadRepositories() {
        try {
            const { data: repositories, error } = await this.supabase
                .from('repositories')
                .select('*')
                .order('star_count', { ascending: false });
            
            if (error) throw error;
            
            this.repositories = repositories || [];
            this.renderRepositories();
            
        } catch (error) {
            console.error('Error loading repositories:', error);
            this.showToast('Error loading repositories', 'error');
        }
    }
    
    renderRepositories() {
        const container = document.getElementById('repositories-grid');
        if (!container) return;
        
        container.innerHTML = this.repositories.map(repo => `
            <div class="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-gray-900">${repo.name}</h3>
                    ${repo.star_count ? `<span class="flex items-center text-sm text-gray-500">⭐ ${repo.star_count}</span>` : ''}
                </div>
                <p class="text-gray-600 text-sm mb-4 line-clamp-3">${repo.description || 'No description available'}</p>
                <div class="flex items-center justify-between">
                    <span class="text-xs text-gray-500">${repo.language || 'Unknown'}</span>
                    <a href="/agents?repository=${repo.id}" class="text-purple-600 hover:text-purple-700 text-sm font-medium">
                        View Agents →
                    </a>
                </div>
            </div>
        `).join('');
    }
    
    async loadAgents() {
        const container = document.getElementById('agents-grid');
        const loading = document.getElementById('agents-loading');
        const empty = document.getElementById('agents-empty');
        
        if (!container) return;
        
        // Show loading
        if (loading) loading.classList.remove('hidden');
        if (empty) empty.classList.add('hidden');
        
        try {
            let query = this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*),
                    tech_stacks(*)
                `, { count: 'exact' });
            
            // Apply filters
            if (this.filters.search) {
                query = query.or(`name.ilike.%${this.filters.search}%,description.ilike.%${this.filters.search}%`);
            }
            
            if (this.filters.lifecycle) {
                query = query.filter('classifications.lifecycle_phase', 'eq', this.filters.lifecycle);
            }
            
            if (this.filters.role) {
                query = query.filter('classifications.role_type', 'eq', this.filters.role);
            }
            
            // Apply pagination
            const from = (this.pagination.page - 1) * this.pagination.limit;
            const to = from + this.pagination.limit - 1;
            
            query = query.range(from, to);
            
            // Apply sorting
            const sortSelect = document.getElementById('sort-select');
            const sortBy = sortSelect ? sortSelect.value : 'name';
            
            switch (sortBy) {
                case 'stars':
                    query = query.order('repository.star_count', { ascending: false });
                    break;
                case 'updated':
                    query = query.order('updated_at', { ascending: false });
                    break;
                case 'created':
                    query = query.order('created_at', { ascending: false });
                    break;
                default:
                    query = query.order('name', { ascending: true });
            }
            
            const { data: agents, count, error } = await query;
            
            if (error) throw error;
            
            this.agents = agents || [];
            this.pagination.total = count || 0;
            this.pagination.totalPages = Math.ceil(this.pagination.total / this.pagination.limit);
            
            // Render agents
            this.renderAgents();
            
            // Render pagination
            this.renderPagination();
            
            // Hide loading, show content
            if (loading) loading.classList.add('hidden');
            
            if (this.agents.length === 0) {
                if (empty) empty.classList.remove('hidden');
            }
            
        } catch (error) {
            console.error('Error loading agents:', error);
            this.showToast('Error loading agents', 'error');
            
            if (loading) loading.classList.add('hidden');
        }
    }
    
    renderAgents() {
        const container = document.getElementById('agents-grid');
        if (!container) return;
        
        container.innerHTML = this.agents.map(agent => this.renderAgentCard(agent)).join('');
        
        // Add event listeners to agent cards
        this.attachAgentCardListeners();
    }
    
    renderAgentCard(agent) {
        const primaryClassification = agent.classifications && agent.classifications.length > 0 
            ? agent.classifications[0] 
            : null;
        
        const techTags = agent.tech_stack ? agent.tech_stack.map(t => t.tag).slice(0, 6) : [];
        const hasMoreTags = agent.tech_stack && agent.tech_stack.length > 6;
        
        return `
            <div class="agent-card bg-white rounded-lg shadow-md overflow-hidden">
                <div class="p-6">
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 mb-2">
                                ${agent.name}
                            </h3>
                            <p class="text-gray-600 text-sm mb-3 line-clamp-3" title="${agent.description}">
                                ${agent.description}
                            </p>
                        </div>
                    </div>
                    
                    <!-- Classifications -->
                    ${primaryClassification ? `
                        <div class="flex flex-wrap gap-2 mb-4">
                            <span class="classification-badge lifecycle-${primaryClassification.lifecycle_phase}">
                                ${primaryClassification.lifecycle_phase.replace('-', ' ')}
                            </span>
                            <span class="classification-badge bg-blue-100 text-blue-800">
                                ${primaryClassification.role_type.replace('-', ' ')}
                            </span>
                        </div>
                    ` : ''}
                    
                    <!-- Tech Stack -->
                    ${techTags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mb-4">
                            ${techTags.map(tag => `<span class="tech-tag">${tag}</span>`).join('')}
                            ${hasMoreTags ? `<span class="text-xs text-gray-500">+${agent.tech_stack.length - 6} more</span>` : ''}
                        </div>
                    ` : ''}
                    
                    <!-- Repository Info -->
                    <div class="text-xs text-gray-500 mb-4">
                        From ${agent.repository?.name || 'Unknown'}
                        ${agent.repository?.star_count ? `• ⭐ ${agent.repository.star_count}` : ''}
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex gap-2">
                        <button onclick="app.previewAgent(${agent.id})" class="flex-1 bg-purple-600 text-white py-2 px-4 rounded hover:bg-purple-700 transition-colors text-sm">
                            Meet Partner
                        </button>
                        <button id="team-btn-${agent.id}" onclick="app.toggleTeamSelection(${agent.id})" class="team-btn bg-gray-200 text-gray-700 py-2 px-4 rounded hover:bg-gray-300 transition-colors text-sm">
                            + Team
                        </button>
                        <button id="compare-btn-${agent.id}" onclick="app.toggleComparison(${agent.id})" class="compare-btn bg-blue-200 text-blue-700 py-2 px-4 rounded hover:bg-blue-300 transition-colors text-sm">
                            Compare
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    attachAgentCardListeners() {
        // Event listeners are added via onclick attributes in renderAgentCard
    }
    
    renderPagination() {
        const container = document.getElementById('pagination');
        if (!container) return;
        
        if (this.pagination.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '';
        
        // Previous button
        if (this.pagination.page > 1) {
            html += `<button onclick="app.goToPage(${this.pagination.page - 1})" class="px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50">Previous</button>`;
        }
        
        // Page numbers
        for (let i = 1; i <= this.pagination.totalPages; i++) {
            if (i === this.pagination.page) {
                html += `<button class="px-3 py-2 bg-purple-600 text-white rounded">${i}</button>`;
            } else {
                html += `<button onclick="app.goToPage(${i})" class="px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50">${i}</button>`;
            }
        }
        
        // Next button
        if (this.pagination.page < this.pagination.totalPages) {
            html += `<button onclick="app.goToPage(${this.pagination.page + 1})" class="px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50">Next</button>`;
        }
        
        container.innerHTML = html;
    }
    
    async previewAgent(agentId) {
        try {
            const { data: agent, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*),
                    tech_stacks(*)
                `)
                .eq('id', agentId)
                .single();
            
            if (error) throw error;
            
            this.showAgentModal(agent);
            
        } catch (error) {
            console.error('Error loading agent details:', error);
            this.showToast('Error loading agent details', 'error');
        }
    }
    
    showAgentModal(agent) {
        const modal = document.getElementById('agent-modal');
        const title = document.getElementById('modal-title');
        const content = document.getElementById('modal-content');
        
        if (!modal || !title || !content) return;
        
        title.textContent = agent.name;
        
        const primaryClassification = agent.classifications && agent.classifications.length > 0 
            ? agent.classifications[0] 
            : null;
        
        const techTags = agent.tech_stack ? agent.tech_stack.map(t => t.tag) : [];
        
        content.innerHTML = `
            <div class="space-y-6">
                <!-- Agent Header -->
                <div>
                    <h4 class="text-lg font-semibold text-gray-900 mb-2">${agent.name}</h4>
                    <p class="text-gray-600">${agent.description}</p>
                </div>
                
                <!-- Classifications -->
                ${primaryClassification ? `
                    <div>
                        <h5 class="font-medium text-gray-900 mb-2">Classification</h5>
                        <div class="flex flex-wrap gap-2">
                            <span class="classification-badge lifecycle-${primaryClassification.lifecycle_phase}">
                                ${primaryClassification.lifecycle_phase.replace('-', ' ')}
                            </span>
                            <span class="classification-badge bg-blue-100 text-blue-800">
                                ${primaryClassification.role_type.replace('-', ' ')}
                            </span>
                        </div>
                    </div>
                ` : ''}
                
                <!-- Tech Stack -->
                ${techTags.length > 0 ? `
                    <div>
                        <h5 class="font-medium text-gray-900 mb-2">Technologies</h5>
                        <div class="flex flex-wrap gap-1">
                            ${techTags.map(tag => `<span class="tech-tag">${tag}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <!-- Repository Info -->
                ${agent.repository ? `
                    <div>
                        <h5 class="font-medium text-gray-900 mb-2">Repository</h5>
                        <div class="text-sm text-gray-600">
                            <p><strong>Name:</strong> ${agent.repository.name}</p>
                            <p><strong>Description:</strong> ${agent.repository.description || 'No description'}</p>
                            ${agent.repository.star_count ? `<p><strong>Stars:</strong> ⭐ ${agent.repository.star_count}</p>` : ''}
                            ${agent.repository.language ? `<p><strong>Language:</strong> ${agent.repository.language}</p>` : ''}
                        </div>
                    </div>
                ` : ''}
                
                <!-- System Prompt -->
                ${agent.system_prompt ? `
                    <div>
                        <h5 class="font-medium text-gray-900 mb-2">System Prompt</h5>
                        <div class="bg-gray-50 rounded p-4 text-sm text-gray-700 max-h-96 overflow-y-auto">
                            <pre class="whitespace-pre-wrap">${agent.system_prompt}</pre>
                        </div>
                    </div>
                ` : ''}
                
                <!-- Actions -->
                <div class="flex gap-2 pt-4 border-t">
                    <button onclick="app.toggleTeamSelection(${agent.id}); app.closeAgentModal();" class="flex-1 bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 transition-colors">
                        Add to Team
                    </button>
                    <button onclick="app.toggleComparison(${agent.id}); app.closeAgentModal();" class="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors">
                        Compare
                    </button>
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
    }
    
    closeAgentModal() {
        const modal = document.getElementById('agent-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    toggleTeamSelection(agentId) {
        const button = document.getElementById(`team-btn-${agentId}`);
        if (!button) return;
        
        if (this.selectedAgents.has(agentId)) {
            this.selectedAgents.delete(agentId);
            button.classList.remove('selected');
            button.textContent = '+ Team';
            this.showToast('Agent removed from team', 'success');
        } else {
            this.selectedAgents.add(agentId);
            button.classList.add('selected');
            button.textContent = '✓ Team';
            this.showToast('Agent added to team', 'success');
        }
        
        this.updateSelectionCounter();
    }
    
    toggleComparison(agentId) {
        const button = document.getElementById(`compare-btn-${agentId}`);
        if (!button) return;
        
        if (this.comparisonList.has(agentId)) {
            this.comparisonList.delete(agentId);
            button.classList.remove('selected');
            button.textContent = 'Compare';
            this.showToast('Agent removed from comparison', 'success');
        } else {
            if (this.comparisonList.size >= 10) {
                this.showToast('Maximum 10 agents can be compared', 'warning');
                return;
            }
            this.comparisonList.add(agentId);
            button.classList.add('selected');
            button.textContent = '✓ Compare';
            this.showToast('Agent added to comparison', 'success');
        }
        
        this.updateComparisonCounter();
    }
    
    updateSelectionCounter() {
        const counter = document.getElementById('selection-counter');
        if (counter) {
            counter.textContent = this.selectedAgents.size;
        }
        
        const downloadBtn = document.getElementById('download-btn');
        const downloadCount = document.getElementById('download-count');
        if (downloadBtn && downloadCount) {
            downloadCount.textContent = this.selectedAgents.size;
            downloadBtn.disabled = this.selectedAgents.size === 0;
        }
    }
    
    updateComparisonCounter() {
        const counter = document.getElementById('comparison-counter');
        if (counter) {
            if (this.comparisonList.size > 0) {
                counter.textContent = this.comparisonList.size;
                counter.classList.remove('hidden');
            } else {
                counter.classList.add('hidden');
            }
        }
        
        const compareBtn = document.getElementById('compare-btn');
        const compareCount = document.getElementById('compare-count');
        if (compareBtn && compareCount) {
            compareCount.textContent = this.comparisonList.size;
            compareBtn.disabled = this.comparisonList.size === 0;
        }
    }
    
    updateCounters() {
        this.updateSelectionCounter();
        this.updateComparisonCounter();
    }
    
    resetFilters() {
        this.filters = {
            search: '',
            lifecycle: '',
            role: '',
            repository: '',
            tech_stack: []
        };
        
        // Reset form elements
        const searchInput = document.getElementById('quick-search');
        const lifecycleFilter = document.getElementById('lifecycle-filter');
        const roleFilter = document.getElementById('role-filter');
        
        if (searchInput) searchInput.value = '';
        if (lifecycleFilter) lifecycleFilter.value = '';
        if (roleFilter) roleFilter.value = '';
        
        this.pagination.page = 1;
        this.loadAgents();
    }
    
    goToPage(page) {
        this.pagination.page = page;
        this.loadAgents();
    }
    
    navigateToCompare() {
        if (this.comparisonList.size === 0) {
            this.showToast('Please select agents to compare', 'warning');
            return;
        }
        
        // Store comparison list in localStorage
        localStorage.setItem('comparison_list', JSON.stringify([...this.comparisonList]));
        
        // Navigate to compare page
        this.handleNavigation('/compare');
    }
    
    navigateToDownload() {
        if (this.selectedAgents.size === 0) {
            this.showToast('Please select agents to download', 'warning');
            return;
        }
        
        // Store selection in localStorage
        localStorage.setItem('selected_agents', JSON.stringify([...this.selectedAgents]));
        
        // Navigate to download page
        this.handleNavigation('/download');
    }
    
    handleNavigation(path) {
        // Simple SPA navigation
        console.log(`Navigating to: ${path}`);
        
        // For now, just show a toast
        this.showToast(`Navigation to ${path} - Feature coming soon!`, 'info');
    }
    
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }
    
    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = 'none';
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        const bgColor = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        }[type] || 'bg-gray-500';
        
        toast.className = `${bgColor} text-white px-4 py-2 rounded-lg shadow-lg mb-2 transition-all duration-300`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (container.contains(toast)) {
                    container.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Global functions for onclick handlers
let app;

function toggleSelection() {
    if (app) {
        app.navigateToDownload();
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app = new SubagentGuildApp();
    
    // Make app globally available for onclick handlers
    window.app = app;
    
    // Load comparison list from localStorage
    const savedComparison = localStorage.getItem('comparison_list');
    if (savedComparison) {
        try {
            app.comparisonList = new Set(JSON.parse(savedComparison));
            app.updateComparisonCounter();
        } catch (e) {
            console.error('Error loading comparison list:', e);
        }
    }
    
    // Load selected agents from localStorage
    const savedSelection = localStorage.getItem('selected_agents');
    if (savedSelection) {
        try {
            app.selectedAgents = new Set(JSON.parse(savedSelection));
            app.updateSelectionCounter();
        } catch (e) {
            console.error('Error loading selected agents:', e);
        }
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SubagentGuildApp;
}