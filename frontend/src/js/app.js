// Subagent Guild Application
// Complete rewrite to match original FastAPI + HTMX functionality

class SubagentGuildApp {
    constructor() {
        // Configuration - use Supabase directly
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
            techStacks: []
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
        
        // Get current page path
        const currentPath = this.getCurrentPagePath();
        console.log(`Current page: ${currentPath}`);
        
        // Initialize page-specific functionality
        await this.initializePage(currentPath);
        
        console.log('✅ Subagent Guild initialized successfully');
    }
    
    getCurrentPagePath() {
        // Get current page path from URL
        const path = window.location.pathname;
        
        // Handle file:// URLs (local development)
        if (path.includes('/index.html')) {
            return '/';
        } else if (path.includes('/agents.html')) {
            return '/agents';
        } else if (path.includes('/compare.html')) {
            return '/compare';
        } else if (path.includes('/repositories.html')) {
            return '/repositories';
        } else if (path.includes('/about.html')) {
            return '/about';
        } else if (path.includes('/download.html')) {
            return '/download';
        }
        
        // For server URLs, remove .html extension if present
        return path.replace(/\.html$/, '');
    }
    
    async initializePage(path) {
        try {
            switch (path) {
                case '/':
                case '/index':
                    await this.initializeHomePage();
                    break;
                case '/agents':
                    await this.initializeAgentsPage();
                    break;
                case '/compare':
                    await this.initializeComparePage();
                    break;
                case '/repositories':
                    await this.initializeRepositoriesPage();
                    break;
                case '/about':
                    await this.initializeAboutPage();
                    break;
                case '/download':
                    await this.initializeDownloadPage();
                    break;
                default:
                    console.warn(`Unknown page path: ${path}`);
                    // Default to home page initialization
                    await this.initializeHomePage();
            }
        } catch (error) {
            console.error('Error initializing page:', error);
            this.showToast('Error initializing page', 'error');
        }
    }
    
    async initializeHomePage() {
        // Load stats and repositories for home page
        await this.loadStats();
        await this.loadRepositories();
        this.updateCounters();
        this.hideLoading();
    }
    
    async initializeAgentsPage() {
        // Load agents data for agents page
        await this.loadStats();
        await this.loadRepositories();
        await this.loadAgents();
        this.updateCounters();
        this.hideLoading();
    }
    
    async initializeComparePage() {
        // Initialize compare page
        await this.loadComparePageData();
        this.hideLoading();
    }
    
    async initializeRepositoriesPage() {
        // Initialize repositories page
        await this.loadRepositories();
        await this.loadRepositoriesPageData();
        this.hideLoading();
    }
    
    async initializeAboutPage() {
        // About page doesn't need specific data loading
        this.hideLoading();
    }
    
    async initializeDownloadPage() {
        // Initialize download page
        await this.loadDownloadPageData();
        this.hideLoading();
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
                this.pagination.page = 1; // Reset to first page
                this.saveFiltersToURL();
                this.loadAgents();
            }, 500));
        }
        
        // Lifecycle filter
        const lifecycleFilter = document.getElementById('lifecycle-filter');
        if (lifecycleFilter) {
            lifecycleFilter.addEventListener('change', () => {
                this.filters.lifecycle = lifecycleFilter.value;
                this.pagination.page = 1; // Reset to first page
                this.saveFiltersToURL();
                this.loadAgents();
            });
        }
        
        // Role filter
        const roleFilter = document.getElementById('role-filter');
        if (roleFilter) {
            roleFilter.addEventListener('change', () => {
                this.filters.role = roleFilter.value;
                this.pagination.page = 1; // Reset to first page
                this.saveFiltersToURL();
                this.loadAgents();
            });
        }
        
        // Repository filter
        const repositoryFilter = document.getElementById('repository-filter');
        if (repositoryFilter) {
            repositoryFilter.addEventListener('change', () => {
                this.filters.repository = repositoryFilter.value;
                this.pagination.page = 1; // Reset to first page
                this.saveFiltersToURL();
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
            const { data: agents, error: agentsError, count } = await this.supabase
                .from('agents')
                .select('*', { count: 'exact', head: true });
            
            if (agentsError) throw agentsError;
            const agentsCount = count || 0;
            
            // Load repositories count
            const { data: repositories, error: reposError, count: reposCount } = await this.supabase
                .from('repositories')
                .select('*', { count: 'exact', head: true });
            
            if (reposError) throw reposError;
            
            // For now, use default values for classification rate and lifecycle count
            const classificationRate = 85; // Default value
            const uniqueLifecycles = 7; // Default value based on config
            
            // Update UI
            this.updateElement('total-agents', agentsCount);
            this.updateElement('total-repositories', reposCount || 0);
            this.updateElement('classification-rate', `${classificationRate}%`);
            this.updateElement('lifecycle-count', uniqueLifecycles);
            
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
                const { data: classifications, error: classificationsError } = await this.supabase
                    .from('classifications')
                    .select('agent_id', { count: 'exact', head: true })
                    .eq('lifecycle_phase', phase);
                
                if (classificationsError) throw classificationsError;
                
                const count = classifications?.length || 0;
                const elementId = `${phase.replace('-', '')}-phase-count`;
                this.updateElement(elementId, count);
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
                .eq('is_active', true)
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
                    <a href="/agents.html?repository=${repo.id}" class="text-purple-600 hover:text-purple-700 text-sm font-medium">
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
            // Build Supabase query
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
                query = query.or(`name.ilike.%${this.filters.search}%,description.ilike.%${this.filters.search}%,system_prompt.ilike.%${this.filters.search}%`);
            }
            
            // Note: For related table filtering in Supabase, we need to use the correct syntax
            // The filter might not work as expected with the current approach
            
            if (this.filters.repository) {
                query = query.eq('repository_id', this.filters.repository);
            }
            
            // For client-side filtering, fetch a larger dataset
            // Limit to 1000 records to avoid excessive data transfer
            query = query.range(0, 999);
            
            // Apply sorting
            const sortSelect = document.getElementById('sort-select');
            const sortBy = sortSelect ? sortSelect.value : 'name';
            
            switch (sortBy) {
                case 'name':
                    query = query.order('name', { ascending: true });
                    break;
                case 'recent':
                    query = query.order('created_at', { ascending: false });
                    break;
                case 'popularity':
                    // For popularity, we'll sort by name (repository sorting is complex with joins)
                    query = query.order('name', { ascending: true });
                    break;
                default:
                    query = query.order('name', { ascending: true });
            }
            
            const { data: agents, error, count } = await query;
            
            if (error) throw error;
            
            console.log('Supabase Response:', agents); // Debug log
            
            // Apply client-side filtering for complex filters
            let filteredAgents = agents || [];
            console.log('Initial agents count:', filteredAgents.length);
            console.log('Applied filters:', this.filters);
            
            // Apply lifecycle filter
            if (this.filters.lifecycle) {
                const beforeCount = filteredAgents.length;
                filteredAgents = filteredAgents.filter(agent => 
                    agent.classifications && agent.classifications.some(c => c.lifecycle_phase === this.filters.lifecycle)
                );
                console.log(`Lifecycle filter "${this.filters.lifecycle}": ${beforeCount} -> ${filteredAgents.length}`);
            }
            
            // Apply role filter
            if (this.filters.role) {
                const beforeCount = filteredAgents.length;
                filteredAgents = filteredAgents.filter(agent => 
                    agent.classifications && agent.classifications.some(c => c.role_type === this.filters.role)
                );
                console.log(`Role filter "${this.filters.role}": ${beforeCount} -> ${filteredAgents.length}`);
            }
            
            // Apply tech stack filters
            if (this.filters.techStacks && this.filters.techStacks.length > 0) {
                const beforeCount = filteredAgents.length;
                filteredAgents = filteredAgents.filter(agent => 
                    agent.tech_stacks && agent.tech_stacks.some(ts => this.filters.techStacks.includes(ts.tag))
                );
                console.log(`Tech stack filter [${this.filters.techStacks.join(', ')}]: ${beforeCount} -> ${filteredAgents.length}`);
            }
            
            // Apply pagination after filtering
            const offset = (this.pagination.page - 1) * this.pagination.limit;
            const paginatedAgents = filteredAgents.slice(offset, offset + this.pagination.limit);
            
            this.agents = paginatedAgents;
            this.pagination.total = filteredAgents.length;
            this.pagination.totalPages = Math.ceil(this.pagination.total / this.pagination.limit);
            
            console.log('Loaded agents:', this.agents.length, 'Total:', this.pagination.total); // Debug log
            
            // Update agents found count
            console.log('Updating results-count to:', this.pagination.total); // Debug log
            this.updateElement('results-count', this.pagination.total);
            
            // Render agents
            console.log('Rendering agents...'); // Debug log
            this.renderAgents();
            console.log('Agents rendered'); // Debug log
            
            // Render pagination
            this.renderPagination();
            
            // Hide loading, show content
            console.log('Hiding loading element:', loading); // Debug log
            if (loading) {
                loading.classList.add('hidden');
                console.log('Loading element hidden'); // Debug log
            } else {
                console.log('Loading element not found'); // Debug log
            }
            
            // Show agents grid
            const agentsGrid = document.getElementById('agents-grid');
            if (agentsGrid) {
                agentsGrid.classList.remove('hidden');
                console.log('Agents grid shown'); // Debug log
            }
            
            // Show pagination if needed
            const pagination = document.getElementById('pagination');
            if (pagination && this.pagination.totalPages > 1) {
                pagination.style.display = 'flex';
                console.log('Pagination shown'); // Debug log
            }
            
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
        if (!container) {
            console.log('Agents grid container not found'); // Debug log
            return;
        }
        
        console.log('Rendering', this.agents.length, 'agents to container:', container); // Debug log
        
        container.innerHTML = this.agents.map(agent => this.renderAgentCard(agent)).join('');
        
        console.log('Container HTML updated'); // Debug log
        
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
        const pageNumbers = document.getElementById('page-numbers');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        if (!container || !pageNumbers || !prevButton || !nextButton) return;
        
        if (this.pagination.totalPages <= 1) {
            container.style.display = 'none';
            return;
        }
        
        // Show pagination container
        container.style.display = 'flex';
        
        // Update previous button
        prevButton.disabled = this.pagination.page <= 1;
        prevButton.onclick = () => this.goToPage(this.pagination.page - 1);
        
        // Update next button
        nextButton.disabled = this.pagination.page >= this.pagination.totalPages;
        nextButton.onclick = () => this.goToPage(this.pagination.page + 1);
        
        // Generate page numbers
        let pageNumbersHtml = '';
        const maxVisiblePages = 5;
        let startPage = Math.max(1, this.pagination.page - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(this.pagination.totalPages, startPage + maxVisiblePages - 1);
        
        if (endPage - startPage < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        // First page and ellipsis
        if (startPage > 1) {
            pageNumbersHtml += `<button onclick="app.goToPage(1)" class="px-3 py-1 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">1</button>`;
            if (startPage > 2) {
                pageNumbersHtml += `<span class="px-2 text-gray-500">...</span>`;
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            if (i === this.pagination.page) {
                pageNumbersHtml += `<button class="px-3 py-1 text-sm bg-purple-600 text-white border border-purple-600 rounded-md">${i}</button>`;
            } else {
                pageNumbersHtml += `<button onclick="app.goToPage(${i})" class="px-3 py-1 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">${i}</button>`;
            }
        }
        
        // Last page and ellipsis
        if (endPage < this.pagination.totalPages) {
            if (endPage < this.pagination.totalPages - 1) {
                pageNumbersHtml += `<span class="px-2 text-gray-500">...</span>`;
            }
            pageNumbersHtml += `<button onclick="app.goToPage(${this.pagination.totalPages})" class="px-3 py-1 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">${this.pagination.totalPages}</button>`;
        }
        
        pageNumbers.innerHTML = pageNumbersHtml;
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
        modal.classList.add('flex');
    }
    
    closeAgentModal() {
        const modal = document.getElementById('agent-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
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
        
        // Save selection to localStorage for download page
        localStorage.setItem('selected_agents', JSON.stringify([...this.selectedAgents]));
    }
    
    toggleComparison(agentId) {
        const button = document.getElementById(`compare-btn-${agentId}`);
        if (!button) {
            console.error(`Compare button not found for agent ${agentId}`);
            return;
        }
        
        console.log(`Toggling comparison for agent ${agentId}, current list size: ${this.comparisonList.size}`);
        
        if (this.comparisonList.has(agentId)) {
            this.comparisonList.delete(agentId);
            button.classList.remove('selected');
            button.textContent = 'Compare';
            this.showToast('Agent removed from comparison', 'success');
            console.log(`Agent ${agentId} removed from comparison, new size: ${this.comparisonList.size}`);
        } else {
            if (this.comparisonList.size >= 10) {
                this.showToast('Maximum 10 agents can be compared', 'warning');
                return;
            }
            this.comparisonList.add(agentId);
            button.classList.add('selected');
            button.textContent = '✓ Compare';
            this.showToast('Agent added to comparison', 'success');
            console.log(`Agent ${agentId} added to comparison, new size: ${this.comparisonList.size}`);
        }
        
        // Save to localStorage
        localStorage.setItem('comparison_list', JSON.stringify([...this.comparisonList]));
        console.log('Comparison list saved to localStorage:', [...this.comparisonList]);
        
        this.updateComparisonCounter();
        console.log('Comparison counter updated');
    }
    
    updateSelectionCounter() {
        // Get selection count from localStorage
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        const count = selectedAgents.length;
        
        // Update main counter
        const counter = document.getElementById('selection-counter');
        if (counter) {
            counter.textContent = count;
        }
        
        // Update badge in navigation
        const badge = document.getElementById('selection-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
        
        const downloadBtn = document.getElementById('download-btn');
        const downloadCount = document.getElementById('download-count');
        if (downloadBtn && downloadCount) {
            downloadCount.textContent = count;
            downloadBtn.disabled = count === 0;
        }
    }
    
    updateComparisonCounter() {
        console.log(`Updating comparison counter, list size: ${this.comparisonList.size}`);
        
        // Update selection panel
        const selectionPanel = document.getElementById('selection-panel');
        const selectedCount = document.getElementById('selected-count');
        
        if (selectionPanel && selectedCount) {
            if (this.comparisonList.size > 0) {
                selectedCount.textContent = this.comparisonList.size;
                selectionPanel.style.display = 'block';
                console.log('Selection panel shown with count:', this.comparisonList.size);
            } else {
                selectionPanel.style.display = 'none';
                console.log('Selection panel hidden');
            }
        } else {
            console.log('Selection panel or selected count element not found');
        }
        
        const compareBtn = document.getElementById('compare-btn');
        const compareCount = document.getElementById('compare-count');
        if (compareBtn && compareCount) {
            compareCount.textContent = this.comparisonList.size;
            compareBtn.disabled = this.comparisonList.size === 0;
            console.log('Compare button updated');
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
            techStacks: []
        };
        
        // Reset form elements
        const searchInput = document.getElementById('quick-search');
        const lifecycleFilter = document.getElementById('lifecycle-filter');
        const roleFilter = document.getElementById('role-filter');
        const repositoryFilter = document.getElementById('repository-filter');
        
        if (searchInput) searchInput.value = '';
        if (lifecycleFilter) lifecycleFilter.value = '';
        if (roleFilter) roleFilter.value = '';
        if (repositoryFilter) repositoryFilter.value = '';
        
        // Reset tech stack checkboxes
        document.querySelectorAll('.tech-stack-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        this.pagination.page = 1;
        this.saveFiltersToURL();
        this.loadAgents();
    }
    
    goToPage(page) {
        this.pagination.page = page;
        this.saveFiltersToURL();
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
        // Navigate to actual HTML pages
        console.log(`Navigating to: ${path}`);
        
        // For local development, check if we're on webpack dev server (localhost:8080) or file:// protocol
        const isLocalDevelopment = window.location.protocol === 'file:' || 
                                  (window.location.hostname === 'localhost' && window.location.port === '8080');
        
        // Map paths to actual HTML files
        const pageMap = {
            '/': isLocalDevelopment ? './index.html' : '/index.html',
            '/agents': isLocalDevelopment ? './agents.html' : '/agents.html',
            '/compare': isLocalDevelopment ? './compare.html' : '/compare.html', 
            '/repositories': isLocalDevelopment ? './repositories.html' : '/repositories.html',
            '/about': isLocalDevelopment ? './about.html' : '/about.html',
            '/download': isLocalDevelopment ? './download.html' : '/download.html'
        };
        
        // Get the actual file path
        const filePath = pageMap[path] || path;
        
        // Navigate to the page
        window.location.href = filePath;
    }
    
    async loadPage(path) {
        // Hide all page-specific elements first
        this.hideAllPages();
        
        try {
            switch (path) {
                case '/':
                case '/index':
                case '/agents':
                case '/agents.html':
                    await this.loadAgentsPage();
                    break;
                case '/compare':
                case '/compare.html':
                    await this.loadComparePage();
                    break;
                case '/repositories':
                case '/repositories.html':
                    await this.loadRepositoriesPage();
                    break;
                case '/about':
                case '/about.html':
                    await this.loadAboutPage();
                    break;
                case '/download':
                case '/download.html':
                    await this.loadDownloadPage();
                    break;
                default:
                    console.warn(`Unknown path: ${path}`);
                    this.showToast('Page not found', 'error');
            }
        } catch (error) {
            console.error('Error loading page:', error);
            this.showToast('Error loading page', 'error');
        }
    }
    
    hideAllPages() {
        // Hide all page-specific loading states and content
        const elements = [
            'agents-loading', 'agents-empty', 'agents-grid', 'pagination',
            'compare-empty', 'compare-content', 'team-analysis', 'compatibility-insights',
            'loading', 'repositories-grid',
            'selection-list', 'popular-agents', 'download_progress'
        ];
        
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.classList.add('hidden');
            }
        });
    }
    
    async loadAgentsPage() {
        // Show agents page elements
        const agentsLoading = document.getElementById('agents-loading');
        if (agentsLoading) agentsLoading.classList.remove('hidden');
        
        // Update navigation
        this.updateActiveNav('/agents');
        
        // Load filters from URL
        this.loadFiltersFromURL();
        
        // Load agents data
        await this.loadAgents();
        await this.loadAgentsStats();
        await this.loadFilterOptions();
    }
    
    async loadAgentsStats() {
        try {
            // Load total agents count
            const { data: agents, error: agentsError, count } = await this.supabase
                .from('agents')
                .select('*', { count: 'exact', head: true });
            
            if (agentsError) throw agentsError;
            const agentsCount = count || 0;
            
            // Load repositories count for filter
            const { data: repositories, error: reposError } = await this.supabase
                .from('repositories')
                .select('*')
                .eq('is_active', true);
            
            if (reposError) throw reposError;
            const reposCount = repositories?.length || 0;
            
            // Update UI
            this.updateElement('total-agents', agentsCount);
            this.updateElement('total-repos', reposCount);
            
        } catch (error) {
            console.error('Error loading agents stats:', error);
        }
    }
    
    async loadFilterOptions() {
        try {
            // Load repositories for filter
            const { data: repositories, error } = await this.supabase
                .from('repositories')
                .select('*')
                .eq('is_active', true)
                .order('name', { ascending: true });
            
            if (error) throw error;
            
            // Update repository filter dropdown
            const repoFilter = document.getElementById('repository-filter');
            if (repoFilter) {
                repoFilter.innerHTML = '<option value="">All Halls</option>' + 
                    repositories.map(repo => `<option value="${repo.id}">${repo.name}</option>`).join('');
            }
            
            // For roles, we'll use a predefined list based on the configuration
            // These are the standard role types from the backend
            const standardRoles = [
                'general',
                'product-manager',
                'system-architect',
                'backend-developer',
                'frontend-developer',
                'performance-engineer',
                'devops-engineer',
                'qa-tester',
                'security-specialist',
                'data-engineer',
                'api-designer',
                'database-developer',
                'mobile-developer',
                'ui-ux-designer'
            ];
            
            // Update role filter dropdown
            const roleFilter = document.getElementById('role-filter');
            if (roleFilter) {
                roleFilter.innerHTML = '<option value="">All Roles</option>' + 
                    standardRoles.map(role => {
                        const formattedRole = role.replace(/-/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase());
                        return `<option value="${role}">${formattedRole}</option>`;
                    }).join('');
            }
            
            // Load tech stack options
            await this.loadTechStackOptions();
            
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }
    
    applyFilters() {
        // Get selected tech stacks
        const selectedTechStacks = Array.from(document.querySelectorAll('.tech-stack-checkbox:checked'))
            .map(checkbox => checkbox.value);
        
        this.filters.techStacks = selectedTechStacks;
        this.pagination.page = 1; // Reset to first page when filters change
        this.saveFiltersToURL();
        this.loadAgents();
    }
    
    saveFiltersToURL() {
        const params = new URLSearchParams();
        
        if (this.filters.search) params.set('search', this.filters.search);
        if (this.filters.lifecycle) params.set('lifecycle', this.filters.lifecycle);
        if (this.filters.role) params.set('role', this.filters.role);
        if (this.filters.repository) params.set('repository', this.filters.repository);
        if (this.filters.techStacks.length > 0) params.set('techStacks', this.filters.techStacks.join(','));
        if (this.pagination.page > 1) params.set('page', this.pagination.page);
        
        const newURL = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.replaceState({}, '', newURL);
    }
    
    loadFiltersFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        this.filters.search = params.get('search') || '';
        this.filters.lifecycle = params.get('lifecycle') || '';
        this.filters.role = params.get('role') || '';
        this.filters.repository = params.get('repository') || '';
        this.filters.techStacks = params.get('techStacks') ? params.get('techStacks').split(',') : [];
        this.pagination.page = parseInt(params.get('page')) || 1;
        
        // Update UI elements
        const searchInput = document.getElementById('quick-search');
        if (searchInput) searchInput.value = this.filters.search;
        
        const lifecycleFilter = document.getElementById('lifecycle-filter');
        if (lifecycleFilter) lifecycleFilter.value = this.filters.lifecycle;
        
        const roleFilter = document.getElementById('role-filter');
        if (roleFilter) roleFilter.value = this.filters.role;
        
        const repositoryFilter = document.getElementById('repository-filter');
        if (repositoryFilter) repositoryFilter.value = this.filters.repository;
        
        // Update tech stack checkboxes
        document.querySelectorAll('.tech-stack-checkbox').forEach(checkbox => {
            checkbox.checked = this.filters.techStacks.includes(checkbox.value);
        });
    }
    
    async loadTechStackOptions() {
        try {
            // Get popular tech stacks from agents
            const { data: techStacks, error } = await this.supabase
                .from('tech_stacks')
                .select('tag, count')
                .order('count', { ascending: false })
                .limit(20);
            
            if (error) throw error;
            
            // Update tech stack filter
            const techStackFilter = document.getElementById('tech-stack-filter');
            if (techStackFilter) {
                techStackFilter.innerHTML = techStacks.map(tech => `
                    <label class="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                        <input type="checkbox" value="${tech.tag}" class="tech-stack-checkbox rounded border-gray-300 text-purple-600 focus:ring-purple-500">
                        <span class="text-sm text-gray-700">${tech.tag}</span>
                        <span class="text-xs text-gray-500">(${tech.count})</span>
                    </label>
                `).join('');
                
                // Add event listeners to checkboxes
                techStackFilter.querySelectorAll('.tech-stack-checkbox').forEach(checkbox => {
                    checkbox.addEventListener('change', () => this.applyFilters());
                });
            }
            
        } catch (error) {
            console.error('Error loading tech stack options:', error);
        }
    }
    
    async loadComparePage() {
        // Update navigation
        this.updateActiveNav('/compare');
        
        // Setup event listeners
        this.setupComparePageEventListeners();
        
        // Load comparison data
        await this.loadComparisonData();
    }
    
    setupComparePageEventListeners() {
        // Add more partners button
        const addMoreBtn = document.getElementById('add-more-btn');
        if (addMoreBtn) {
            addMoreBtn.onclick = () => {
                window.location.href = '/agents.html';
            };
        }
        
        // Clear all button
        const clearAllBtn = document.getElementById('clear-all-btn');
        if (clearAllBtn) {
            clearAllBtn.onclick = () => {
                this.clearAllComparisons();
            };
        }
        
        // Save comparison button
        const saveComparisonBtn = document.getElementById('save-comparison-btn');
        if (saveComparisonBtn) {
            saveComparisonBtn.onclick = () => {
                this.saveComparison();
            };
        }
        
        // Download comparison button
        const downloadComparisonBtn = document.getElementById('download-comparison-btn');
        if (downloadComparisonBtn) {
            downloadComparisonBtn.onclick = () => {
                this.downloadComparison();
            };
        }
        
        // Share comparison button
        const shareComparisonBtn = document.getElementById('share-comparison-btn');
        if (shareComparisonBtn) {
            shareComparisonBtn.onclick = () => {
                this.shareComparison();
            };
        }
    }
    
    clearAllComparisons() {
        this.comparisonList.clear();
        localStorage.setItem('comparison_list', JSON.stringify([]));
        this.updateComparisonCounter();
        this.loadComparisonData();
        this.showToast('All comparisons cleared', 'success');
    }
    
    saveComparison() {
        const comparisonList = JSON.parse(localStorage.getItem('comparison_list') || '[]');
        if (comparisonList.length === 0) {
            this.showToast('No agents to save', 'warning');
            return;
        }
        
        const name = prompt('Enter a name for this comparison:');
        if (!name) return;
        
        const savedComparisons = JSON.parse(localStorage.getItem('saved_comparisons') || '[]');
        savedComparisons.push({
            id: Date.now(),
            name: name,
            agentIds: comparisonList,
            timestamp: new Date().toISOString()
        });
        
        localStorage.setItem('saved_comparisons', JSON.stringify(savedComparisons));
        this.showToast('Comparison saved successfully', 'success');
    }
    
    downloadComparison() {
        const comparisonList = JSON.parse(localStorage.getItem('comparison_list') || '[]');
        if (comparisonList.length === 0) {
            this.showToast('No agents to download', 'warning');
            return;
        }
        
        // Create a simple text report
        const report = `AI Partners Comparison Report\nGenerated: ${new Date().toLocaleDateString()}\n\nAgents compared: ${comparisonList.length}\n\n`;
        
        // Create blob and download
        const blob = new Blob([report], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comparison-report-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showToast('Comparison report downloaded', 'success');
    }
    
    shareComparison() {
        const comparisonList = JSON.parse(localStorage.getItem('comparison_list') || '[]');
        if (comparisonList.length === 0) {
            this.showToast('No agents to share', 'warning');
            return;
        }
        
        const shareUrl = `${window.location.origin}/compare.html?agent_ids=${comparisonList.join(',')}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'AI Partners Comparison',
                text: `Check out this comparison of ${comparisonList.length} AI partners`,
                url: shareUrl
            });
        } else {
            // Fallback - copy to clipboard
            navigator.clipboard.writeText(shareUrl).then(() => {
                this.showToast('Comparison link copied to clipboard', 'success');
            }).catch(() => {
                this.showToast('Failed to copy link', 'error');
            });
        }
    }
    
    async downloadSelectedAgents() {
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        if (selectedAgents.length === 0) {
            this.showToast('No partners selected to download', 'warning');
            return;
        }
        
        try {
            // Show progress
            const downloadBtn = document.getElementById('download_btn');
            const progressContainer = document.getElementById('download_progress');
            const progressBar = document.getElementById('progress-bar');
            const progressPercent = document.getElementById('progress-percent');
            
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.textContent = 'Preparing Download...';
            }
            
            if (progressContainer) {
                progressContainer.classList.add('active');
            }
            
            // Update progress
            if (progressBar && progressPercent) {
                progressBar.style.width = '20%';
                progressPercent.textContent = '20%';
            }
            
            // Fetch agent data
            const { data: agents, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*)
                `)
                .in('id', selectedAgents);
            
            if (error) throw error;
            
            if (!agents || agents.length === 0) {
                this.showToast('No agent data found', 'error');
                return;
            }
            
            // Update progress
            if (progressBar && progressPercent) {
                progressBar.style.width = '60%';
                progressPercent.textContent = '60%';
            }
            
            // Create package content
            const packageName = document.getElementById('package_name')?.value || 'my_ai_team';
            const includeReadme = document.getElementById('include_readme')?.checked !== false;
            
            // Create ZIP package
            const zip = new JSZip();
            
            // Add README if requested
            if (includeReadme) {
                let readmeContent = `# ${packageName}\n\n`;
                readmeContent += `## AI Partners Package\n\n`;
                readmeContent += `Generated: ${new Date().toLocaleDateString()}\n\n`;
                readmeContent += `This package contains ${agents.length} AI partners:\n\n`;
                
                agents.forEach((agent, index) => {
                    readmeContent += `${index + 1}. **${agent.name}** - ${agent.description}\n`;
                });
                
                readmeContent += `\n## Installation\n\n`;
                readmeContent += `Each agent is designed to work with Claude Code. Follow the specific instructions for each agent.\n\n`;
                readmeContent += `## Agents Included\n\n`;
                
                agents.forEach((agent, index) => {
                    const lifecyclePhase = agent.classifications?.lifecycle_phase || 'general';
                    const roleType = agent.classifications?.role_type || 'general';
                    
                    readmeContent += `### ${index + 1}. ${agent.name}\n\n`;
                    readmeContent += `**Description:** ${agent.description}\n\n`;
                    readmeContent += `**Lifecycle Phase:** ${lifecyclePhase}\n`;
                    readmeContent += `**Role Type:** ${roleType}\n`;
                    readmeContent += `**Repository:** ${agent.repository?.name || 'Unknown'}\n\n`;
                    
                    if (agent.system_prompt) {
                        readmeContent += `**System Prompt:**\n\`\`\`\n${agent.system_prompt}\n\`\`\`\n\n`;
                    }
                    
                    readmeContent += `---\n\n`;
                });
                
                zip.file("README.md", readmeContent);
            }
            
            // Add each agent's details as individual files
            const agentsFolder = zip.folder("agents");
            
            agents.forEach((agent, index) => {
                const lifecyclePhase = agent.classifications?.lifecycle_phase || 'general';
                const roleType = agent.classifications?.role_type || 'general';
                
                // Create individual agent file
                const agentContent = `# ${agent.name}\n\n` +
                    `**Description:** ${agent.description}\n\n` +
                    `**Lifecycle Phase:** ${lifecyclePhase}\n` +
                    `**Role Type:** ${roleType}\n` +
                    `**Repository:** ${agent.repository?.name || 'Unknown'}\n\n` +
                    `**System Prompt:**\n\`\`\`\n${agent.system_prompt || 'No system prompt available'}\n\`\`\`\n\n` +
                    `**Instructions:** ${agent.instructions || 'No specific instructions provided'}\n\n`;
                
                // Sanitize filename
                const safeAgentName = agent.name.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_');
                agentsFolder.file(`${safeAgentName}.md`, agentContent);
            });
            
            // Update progress
            if (progressBar && progressPercent) {
                progressBar.style.width = '90%';
                progressPercent.textContent = '90%';
            }
            
            // Generate and download the ZIP file
            const zipContent = await zip.generateAsync({ type: "blob" });
            const url = URL.createObjectURL(zipContent);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${packageName}-${Date.now()}.zip`;
            a.click();
            URL.revokeObjectURL(url);
            
            // Complete progress
            if (progressBar && progressPercent) {
                progressBar.style.width = '100%';
                progressPercent.textContent = '100%';
            }
            
            // Show success modal
            const modal = document.getElementById('download_modal');
            if (modal) {
                modal.classList.remove('hidden');
                modal.classList.add('flex');
            }
            
            // Reset button after delay
            setTimeout(() => {
                if (downloadBtn) {
                    downloadBtn.disabled = false;
                    downloadBtn.textContent = 'Download Selected Partners';
                }
                
                if (progressContainer) {
                    progressContainer.classList.remove('active');
                }
                
                if (progressBar && progressPercent) {
                    progressBar.style.width = '0%';
                    progressPercent.textContent = '0%';
                }
            }, 2000);
            
            this.showToast('Package downloaded successfully!', 'success');
            
        } catch (error) {
            console.error('Error downloading selected agents:', error);
            this.showToast('Error preparing download', 'error');
            
            // Reset button on error
            const downloadBtn = document.getElementById('download_btn');
            const progressContainer = document.getElementById('download_progress');
            
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.textContent = 'Download Selected Partners';
            }
            
            if (progressContainer) {
                progressContainer.classList.remove('active');
            }
        }
    }
    
    closeDownloadModal() {
        const modal = document.getElementById('download_modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }
    
    createNewPackage() {
        this.closeDownloadModal();
        this.clearAllSelections();
        
        // Reset package name
        const packageNameInput = document.getElementById('package_name');
        if (packageNameInput) {
            packageNameInput.value = 'my_ai_team';
        }
        
        // Reset include readme checkbox
        const includeReadmeCheckbox = document.getElementById('include_readme');
        if (includeReadmeCheckbox) {
            includeReadmeCheckbox.checked = true;
        }
    }
    
    async loadComparisonData() {
        const comparisonList = JSON.parse(localStorage.getItem('comparison_list') || '[]');
        
        console.log('Loading comparison data, list:', comparisonList);
        
        if (comparisonList.length === 0) {
            // Show empty state
            const emptyState = document.getElementById('empty-state');
            const comparisonContainer = document.getElementById('comparison-container');
            const teamAnalysis = document.getElementById('team-analysis');
            const compatibilityInsights = document.getElementById('compatibility-insights');
            
            if (emptyState) emptyState.style.display = 'block';
            if (comparisonContainer) comparisonContainer.style.display = 'none';
            if (teamAnalysis) teamAnalysis.style.display = 'none';
            if (compatibilityInsights) compatibilityInsights.style.display = 'none';
            return;
        }
        
        // Show comparison content
        const emptyState = document.getElementById('empty-state');
        const comparisonContainer = document.getElementById('comparison-container');
        const teamAnalysis = document.getElementById('team-analysis');
        const compatibilityInsights = document.getElementById('compatibility-insights');
        
        if (emptyState) emptyState.style.display = 'none';
        if (comparisonContainer) comparisonContainer.style.display = 'block';
        if (teamAnalysis) teamAnalysis.style.display = 'block';
        if (compatibilityInsights) compatibilityInsights.style.display = 'block';
        
        // Load agents for comparison
        try {
            const { data: agents, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*),
                    tech_stacks(*)
                `)
                .in('id', comparisonList);
            
            if (error) throw error;
            
            this.renderComparisonTable(agents || []);
            this.analyzeTeamCompatibility(agents || []);
            
        } catch (error) {
            console.error('Error loading comparison data:', error);
            this.showToast('Error loading comparison data', 'error');
        }
    }
    
    // Helper function to convert string to title case
    toTitleCase(str) {
        return str.replace(/(?:^|\s)\w/g, match => match.toUpperCase());
    }
    
    renderComparisonTable(agents) {
        const tbody = document.getElementById('comparison-tbody');
        const headerRow = document.querySelector('thead tr');
        if (!tbody || !headerRow) return;
        
        if (agents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" class="text-center py-8 text-gray-500">No agents selected for comparison</td></tr>';
            return;
        }
        
        // Capture method reference for use in template
        const toTitleCase = this.toTitleCase.bind(this);
        
        // Clear existing headers (keep the first "Features" column)
        const existingHeaders = headerRow.querySelectorAll('th.agent-header');
        existingHeaders.forEach(header => header.remove());

        // Generate headers dynamically like the reference implementation
        agents.forEach(agent => {
            const th = document.createElement('th');
            th.className = 'agent-header';
            th.innerHTML = `
                <div class="agent-name">${agent.name}</div>
                <div class="agent-repo">
                    <span>🏰</span>
                    <span>${agent.repository?.name || 'Unknown'}</span>
                    ${agent.repository?.star_count ? `<span>⭐ ${agent.repository.star_count}</span>` : ''}
                </div>
            `;
            headerRow.appendChild(th);
        });
        
        // Build table rows (matching reference structure)
        let html = '';
        
        // Description row
        html += '<tr><td>Description</td>';
        agents.forEach(agent => {
            html += `<td class="description-cell">${agent.description || 'No description'}</td>`;
        });
        html += '</tr>';
        
        // Role Type row
        html += '<tr><td>Role Type</td>';
        agents.forEach(agent => {
            const primaryClassification = agent.classifications && agent.classifications.length > 0 ? agent.classifications[0] : null;
            html += `<td>
                ${primaryClassification 
                    ? `<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                        ${toTitleCase(primaryClassification.role_type.replace('-', ' '))}
                       </span>`
                    : '<span class="text-gray-500">Not classified</span>'}
            </td>`;
        });
        html += '</tr>';
        
        // Lifecycle Phase row
        html += '<tr><td>Lifecycle Phase</td>';
        agents.forEach(agent => {
            const primaryClassification = agent.classifications && agent.classifications.length > 0 ? agent.classifications[0] : null;
            html += `<td>
                ${primaryClassification 
                    ? `<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium lifecycle-${primaryClassification.lifecycle_phase}">
                        ${toTitleCase(primaryClassification.lifecycle_phase.replace('-', ' '))}
                       </span>`
                    : '<span class="text-gray-500">Not classified</span>'}
            </td>`;
        });
        html += '</tr>';
        
        // Technologies row
        html += '<tr><td>Technologies</td>';
        agents.forEach(agent => {
            const techTags = agent.tech_stack ? agent.tech_stack.map(t => t.tag) : [];
            html += `<td>
                ${techTags.length > 0 
                    ? `<div class="tech-grid">${techTags.map(tag => `<span class="tech-tag" data-tech="${tag}">${tag}</span>`).join('')}</div>`
                    : '<span class="text-gray-500">No technologies listed</span>'}
            </td>`;
        });
        html += '</tr>';
        
        // Instructions Preview row
        html += '<tr><td>Instructions Preview</td>';
        agents.forEach(agent => {
            html += `<td>
                ${agent.system_prompt 
                    ? `<div class="instructions-preview">
                        ${agent.system_prompt.substring(0, 500)}${agent.system_prompt.length > 500 ? '...' : ''}
                        ${agent.system_prompt.length > 500 ? `<div class="mt-2"><a href="#" onclick="app.previewAgent(${agent.id}); return false;" class="text-purple-600 hover:text-purple-700 text-xs font-medium">View full instructions →</a></div>` : ''}
                       </div>`
                    : '<span class="text-gray-500 italic">No detailed instructions available</span>'}
            </td>`;
        });
        html += '</tr>';
        
        // Prompt Complexity row
        html += '<tr><td>Prompt Complexity</td>';
        agents.forEach(agent => {
            const promptLength = agent.system_prompt ? agent.system_prompt.length : 0;
            const complexityClass = promptLength > 1000 ? 'complexity-detailed' : promptLength > 500 ? 'complexity-moderate' : 'complexity-simple';
            const complexityText = promptLength > 1000 ? 'Detailed' : promptLength > 500 ? 'Moderate' : 'Simple';
            html += `<td>
                <div class="complexity-badge ${complexityClass}">
                    <span class="font-medium">${promptLength}</span>
                    <span class="text-xs">${complexityText}</span>
                </div>
            </td>`;
        });
        html += '</tr>';
        
        // Actions row
        html += '<tr><td>Actions</td>';
        agents.forEach(agent => {
            html += `<td>
                <div class="flex gap-2">
                    <a href="/agents.html?id=${agent.id}" class="bg-purple-600 text-white py-1 px-3 rounded text-sm font-medium hover:bg-purple-700 transition-colors">
                        View Details
                    </a>
                    <button onclick="app.removeFromComparison(${agent.id})" class="bg-red-500 text-white py-1 px-3 rounded text-sm hover:bg-red-600 transition-colors">
                        Remove
                    </button>
                </div>
            </td>`;
        });
        html += '</tr>';
        
        tbody.innerHTML = html;
    }
    
    analyzeTeamCompatibility(agents) {
        // Analyze shared technologies, roles, etc.
        const allTechTags = new Set();
        const techUsage = {};
        
        agents.forEach(agent => {
            const techTags = agent.tech_stack ? agent.tech_stack.map(t => t.tag) : [];
            techTags.forEach(tag => {
                allTechTags.add(tag);
                techUsage[tag] = (techUsage[tag] || 0) + 1;
            });
        });
        
        const sharedTechnologies = Object.keys(techUsage).filter(tag => techUsage[tag] > 1);
        const uniqueTechnologies = Object.keys(techUsage).filter(tag => techUsage[tag] === 1);
        
        // Update team chemistry analysis
        const chemistryResults = document.getElementById('chemistry-results');
        if (chemistryResults) {
            chemistryResults.innerHTML = `
                <div class="text-center">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <span class="text-2xl">🤝</span>
                    </div>
                    <div class="text-sm font-medium text-gray-900">${sharedTechnologies.length} Shared Technologies</div>
                    <div class="text-xs text-gray-500 mt-1">${sharedTechnologies.slice(0, 3).join(', ')}</div>
                </div>
                
                <div class="text-center">
                    <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <span class="text-2xl">⚖️</span>
                    </div>
                    <div class="text-sm font-medium text-gray-900">Team Balance</div>
                    <div class="text-xs text-gray-500 mt-1">${agents.length} partners selected</div>
                </div>
                
                <div class="text-center">
                    <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <span class="text-2xl">💡</span>
                    </div>
                    <div class="text-sm font-medium text-gray-900">Team Insights</div>
                    <div class="text-xs text-gray-500 mt-1">Ready for collaboration</div>
                </div>
            `;
        }
        
        // Update compatibility insights
        const insightsContent = document.getElementById('insights-content');
        if (insightsContent) {
            let insightsHtml = '';
            
            if (sharedTechnologies.length > 0) {
                insightsHtml += `
                    <div class="bg-green-50 border-l-4 border-green-400 p-4 rounded-lg mb-4">
                        <h3 class="font-medium text-green-800 mb-2">🤝 Shared Technologies</h3>
                        <p class="text-sm text-green-700">
                            These partners share ${sharedTechnologies.length} technologies: 
                            <strong>${sharedTechnologies.join(', ')}</strong>
                        </p>
                    </div>
                `;
            }
            
            if (uniqueTechnologies.length > 0) {
                insightsHtml += `
                    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg mb-4">
                        <h3 class="font-medium text-yellow-800 mb-2">⚡ Unique Specializations</h3>
                        <p class="text-sm text-yellow-700">
                            Team members bring unique expertise in: <strong>${uniqueTechnologies.slice(0, 5).join(', ')}</strong>
                        </p>
                    </div>
                `;
            }
            
            insightsHtml += `
                <div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-lg">
                    <h3 class="font-medium text-blue-800 mb-2">💡 Team Recommendations</h3>
                    <ul class="text-sm text-blue-700 space-y-1">
                        <li>• This team has good technological diversity</li>
                        <li>• Consider assigning complementary tasks based on specializations</li>
                        <li>• Shared technologies enable easier collaboration</li>
                    </ul>
                </div>
            `;
            
            insightsContent.innerHTML = insightsHtml;
        }
    }
    
    removeFromComparison(agentId) {
        this.comparisonList.delete(agentId);
        localStorage.setItem('comparison_list', JSON.stringify([...this.comparisonList]));
        this.updateComparisonCounter();
        this.loadComparisonData(); // Refresh comparison
        this.showToast('Agent removed from comparison', 'success');
    }
    
    async loadRepositoriesPage() {
        // Update navigation
        this.updateActiveNav('/repositories');
        
        // Show loading
        const loading = document.getElementById('loading');
        if (loading) loading.style.display = 'block';
        
        // Load repositories data
        await this.loadRepositoriesPageData();
    }
    
    async loadRepositoriesPageData() {
        try {
            // Load repositories with agent counts
            const { data: repositories, error: reposError } = await this.supabase
                .from('repositories')
                .select(`
                    *,
                    agents(count)
                `)
                .eq('is_active', true)
                .order('star_count', { ascending: false });
            
            if (reposError) throw reposError;
            
            // Get total agents count
            const { data: agents, error: agentsError, count } = await this.supabase
                .from('agents')
                .select('*', { count: 'exact', head: true });
            
            if (agentsError) throw agentsError;
            const totalAgents = count || 0;
            
            // Calculate largest repository count
            const repoAgentCounts = {};
            let largestRepoCount = 0;
            
            if (repositories) {
                repositories.forEach(repo => {
                    const agentCount = repo.agents?.[0]?.count || 0;
                    repoAgentCounts[repo.id] = agentCount;
                    largestRepoCount = Math.max(largestRepoCount, agentCount);
                });
            }
            
            // Update statistics
            this.updateElement('total-repos', repositories?.length || 0);
            
            // Render repositories
            this.renderRepositoriesPage(repositories || [], repoAgentCounts);
            
            // Hide loading
            const loading = document.getElementById('loading');
            if (loading) loading.style.display = 'none';
            
            // Show empty state if needed
            const container = document.getElementById('repositories-grid');
            if (container) {
                if (repositories && repositories.length > 0) {
                    container.style.display = 'grid';
                } else {
                    container.style.display = 'none';
                    container.innerHTML = '<div class="col-span-full text-center py-8"><p class="text-gray-500">No repositories found</p></div>';
                }
            }
            
        } catch (error) {
            console.error('Error loading repositories page data:', error);
            this.showToast('Error loading repositories', 'error');
            
            // Hide loading
            const loading = document.getElementById('loading');
            if (loading) loading.style.display = 'none';
        }
    }
    
    renderRepositoriesPage(repositories, repoAgentCounts) {
        const container = document.getElementById('repositories-grid');
        if (!container) return;
        
        container.innerHTML = repositories.map(repo => {
            const agentCount = repoAgentCounts[repo.id] || 0;
            const isActive = repo.is_active !== false; // Default to true if not specified
            
            return `
                <div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
                    <!-- Repository Header -->
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 mb-1">
                                ${repo.name}
                            </h3>
                            <p class="text-sm text-gray-500">
                                ${repo.owner || 'Unknown'}/${repo.name}
                            </p>
                        </div>
                        ${isActive 
                            ? `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Active</span>`
                            : `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Inactive</span>`}
                    </div>

                    <!-- Description -->
                    ${repo.description 
                        ? `<p class="text-gray-600 text-sm mb-4 line-clamp-3">${repo.description}</p>` 
                        : ''}

                    <!-- Statistics -->
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="text-center">
                            <div class="text-2xl font-bold text-purple-600">${agentCount}</div>
                            <div class="text-xs text-gray-500">Agents</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-blue-600">${repo.star_count || 0}</div>
                            <div class="text-xs text-gray-500">Stars</div>
                        </div>
                    </div>

                    <!-- Last Updated -->
                    ${repo.last_synced 
                        ? `<div class="text-xs text-gray-500 mb-4">
                            Last synced: ${new Date(repo.last_synced).toLocaleDateString()}
                        </div>` 
                        : ''}

                    <!-- Actions -->
                    <div class="flex space-x-2">
                        <a href="/agents.html?repository_id=${repo.id}" 
                           class="flex-1 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium py-2 px-3 rounded-md text-center transition-colors">
                            View Agents
                        </a>
                        ${repo.url 
                            ? `<a href="${repo.url}" 
                               target="_blank" 
                               rel="noopener noreferrer"
                               class="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium py-2 px-3 rounded-md text-center transition-colors">
                                GitHub
                            </a>` 
                            : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    async loadAboutPage() {
        // Update navigation
        this.updateActiveNav('/about');
        
        // About page is mostly static, just ensure it's visible
        console.log('About page loaded');
    }
    
    async loadDownloadPage() {
        // Update navigation
        this.updateActiveNav('/download');
        
        // Load download page data
        await this.loadDownloadPageData();
    }
    
    async loadDownloadPageData() {
        try {
            // Load popular agents
            const { data: popularAgents, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*)
                `)
                .order('created_at', { ascending: false })
                .limit(6);
            
            if (error) throw error;
            
            // Render popular agents
            this.renderPopularAgents(popularAgents || []);
            
            // Load current selection
            await this.loadCurrentSelection();
            
        } catch (error) {
            console.error('Error loading download page data:', error);
            this.showToast('Error loading download page', 'error');
        }
    }
    
    renderPopularAgents(agents) {
        const container = document.getElementById('popular-agents');
        if (!container) return;
        
        // Capture method reference for use in template
        const toTitleCase = this.toTitleCase.bind(this);
        
        container.innerHTML = agents.map(agent => {
            const primaryClassification = agent.classifications && agent.classifications.length > 0 
                ? agent.classifications[0] 
                : null;
            
            return `
                <div class="border rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <h3 class="font-medium text-gray-900 mb-1">${agent.name}</h3>
                            <p class="text-sm text-gray-600 mb-2">
                                ${agent.description ? agent.description.substring(0, 80) + (agent.description.length > 80 ? '...' : '') : 'No description'}
                            </p>
                            
                            ${primaryClassification 
                                ? `<div class="flex gap-2 mb-2">
                                    <span class="classification-badge lifecycle-${primaryClassification.lifecycle_phase}">
                                        ${toTitleCase(primaryClassification.lifecycle_phase.replace('-', ' '))}
                                    </span>
                                </div>` 
                                : ''}
                            
                            <div class="text-xs text-gray-500">
                                ${agent.repository?.name || 'Unknown'}
                            </div>
                        </div>
                        
                        <button 
                            onclick="app.addToSelection(${agent.id})"
                            class="ml-3 bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700 transition-colors"
                        >
                            + Add
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    async loadCurrentSelection() {
        // Ensure the selection list is visible
        const selectionList = document.getElementById('selection-list');
        if (selectionList) {
            selectionList.classList.remove('hidden');
        }
        
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        
        if (selectedAgents.length === 0) {
            // Show empty state
            const selectionList = document.getElementById('selection-list');
            if (selectionList) {
                selectionList.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-4xl mb-2">👥</div>
                        <p class="text-sm">No partners selected yet</p>
                        <p class="text-xs text-gray-400 mt-2">Browse agents to add to your selection</p>
                    </div>
                `;
            }
            
            // Update counters
            this.updateElement('selected-count', 0);
            const downloadBtn = document.getElementById('download_btn');
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.textContent = 'Select Partners to Download';
            }
            return;
        }
        
        try {
            const { data: agents, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classifications(*)
                `)
                .in('id', selectedAgents);
            
            if (error) throw error;
            
            // Ensure DOM is ready before rendering
            await new Promise(resolve => setTimeout(resolve, 0));
            
            this.renderSelectionList(agents || []);
            this.updateDownloadButton(agents || []);
            
        } catch (error) {
            console.error('Error loading current selection:', error);
            this.showToast('Error loading selection', 'error');
        }
    }
    
    renderSelectionList(agents) {
        const container = document.getElementById('selection-list');
        if (!container) return;
        
        if (agents.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <div class="text-4xl mb-2">👥</div>
                    <p class="text-sm">No partners selected yet</p>
                    <p class="text-xs text-gray-400 mt-2">Browse agents to add to your selection</p>
                </div>
            `;
            return;
        }
        
        // Capture method reference for use in template
        const toTitleCase = this.toTitleCase.bind(this);
        
        container.innerHTML = `
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <h3 class="font-medium text-gray-900">Selected Partners (${agents.length})</h3>
                    <button 
                        onclick="app.clearAllSelections()"
                        class="text-sm text-gray-500 hover:text-gray-700"
                    >
                        Clear All
                    </button>
                </div>
                
                ${agents.map(agent => {
                    const primaryClassification = agent.classifications && agent.classifications.length > 0 
                        ? agent.classifications[0] 
                        : null;
                    
                    return `
                        <div class="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                            <div class="flex-1">
                                <div class="text-sm font-medium text-gray-900">${agent.name}</div>
                                <div class="text-xs text-gray-500">
                                    ${primaryClassification 
                                        ? toTitleCase(primaryClassification.role_type.replace('-', ' '))
                                        : 'General'}
                                </div>
                            </div>
                            <button 
                                onclick="app.removeFromSelection(${agent.id})"
                                class="text-red-500 hover:text-red-700 text-sm"
                            >
                                ✕
                            </button>
                        </div>
                    `;
                }).join('')}
                
                <div class="pt-3 border-t border-gray-200">
                    <a href="/compare.html?agent_ids=${agents.map(a => a.id).join(',')}" 
                       class="w-full bg-blue-600 text-white text-center py-2 px-3 rounded text-sm hover:bg-blue-700 transition-colors block">
                        Compare All
                    </a>
                </div>
            </div>
        `;
    }
    
    updateDownloadButton(agents) {
        const count = agents.length;
        
        // Update counter
        this.updateElement('selected-count', count);
        
        // Update download button
        const downloadBtn = document.getElementById('download_btn');
        if (downloadBtn) {
            if (count > 0) {
                downloadBtn.disabled = false;
                downloadBtn.className = "w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-purple-700 transition-colors";
                downloadBtn.textContent = `Download ${count} Partner${count > 1 ? 's' : ''}`;
            } else {
                downloadBtn.disabled = true;
                downloadBtn.className = "w-full bg-gray-400 text-white py-3 px-4 rounded-lg font-semibold transition-colors cursor-not-allowed";
                downloadBtn.textContent = "Select Partners to Download";
            }
        }
    }
    
    addToSelection(agentId) {
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        
        if (!selectedAgents.includes(agentId)) {
            selectedAgents.push(agentId);
            localStorage.setItem('selected_agents', JSON.stringify(selectedAgents));
            this.loadCurrentSelection(); // Refresh the selection list
            this.showToast('Agent added to selection', 'success');
        } else {
            this.showToast('Agent already in selection', 'warning');
        }
    }
    
    removeFromSelection(agentId) {
        let selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        selectedAgents = selectedAgents.filter(id => id !== agentId);
        localStorage.setItem('selected_agents', JSON.stringify(selectedAgents));
        this.loadCurrentSelection(); // Refresh the selection list
        this.showToast('Agent removed from selection', 'success');
    }
    
    clearAllSelections() {
        localStorage.removeItem('selected_agents');
        this.loadCurrentSelection(); // Refresh the selection list
        this.showToast('All selections cleared', 'success');
    }
    
    updateActiveNav(activePath) {
        // Remove active class from all nav links
        document.querySelectorAll('nav a').forEach(link => {
            link.classList.remove('font-semibold');
        });
        
        // Add active class to current nav link
        const activeLink = document.querySelector(`nav a[href="${activePath}"]`);
        if (activeLink) {
            activeLink.classList.add('font-semibold');
        }
    }
    
    updateElement(id, content) {
        const element = document.getElementById(id);
        console.log(`updateElement: Looking for element with id '${id}', found:`, !!element); // Debug log
        if (element) {
            console.log(`updateElement: Setting element '${id}' content to:`, content); // Debug log
            element.textContent = content;
        } else {
            console.log(`updateElement: Element with id '${id}' not found`); // Debug log
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
    
    // Download functionality
    async initiateDownload() {
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        
        if (selectedAgents.length === 0) {
            this.showToast('No partners selected for download!', 'warning');
            return;
        }
        
        const packageName = document.getElementById('package_name')?.value || 'my_ai_team';
        const includeReadme = document.getElementById('include_readme')?.checked ?? true;
        
        // Show progress
        this.showDownloadProgress();
        
        try {
            // Simulate download preparation
            await this.simulateDownloadPreparation();
            
            // Generate package (simplified for demo)
            const packageContent = await this.generatePackage(selectedAgents, packageName, includeReadme);
            
            // Create and trigger download
            this.triggerDownload(packageContent, `${packageName}.zip`);
            
            // Hide progress and show success
            this.hideDownloadProgress();
            this.showDownloadModal();
            this.addToDownloadHistory(packageName, selectedAgents.length);
            
        } catch (error) {
            console.error('Download failed:', error);
            this.hideDownloadProgress();
            this.showToast('Download failed: ' + error.message, 'error');
        }
    }
    
    async simulateDownloadPreparation() {
        // Simulate download progress
        const steps = [
            { percent: 30, text: 'Collecting agent files...' },
            { percent: 60, text: 'Generating documentation...' },
            { percent: 90, text: 'Creating package...' },
            { percent: 100, text: 'Download complete!' }
        ];
        
        for (const step of steps) {
            this.updateProgress(step.percent, step.text);
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    async generatePackage(agentIds, packageName, includeReadme) {
        // In a real implementation, this would generate actual ZIP files
        // For now, we'll create a simple JSON representation
        
        const { data: agents, error } = await this.supabase
            .from('agents')
            .select(`
                *,
                repository:repositories(*),
                classifications(*),
                tech_stacks(*)
            `)
            .in('id', agentIds);
        
        if (error) throw error;
        
        const packageData = {
            name: packageName,
            created_at: new Date().toISOString(),
            include_readme: includeReadme,
            agents: agents,
            metadata: {
                total_agents: agents.length,
                repositories: [...new Set(agents.map(a => a.repository?.name).filter(Boolean))],
                technologies: [...new Set(agents.flatMap(a => a.tech_stack?.map(t => t.tag) || []))]
            }
        };
        
        // Create a simple text representation for demo
        return JSON.stringify(packageData, null, 2);
    }
    
    triggerDownload(content, filename) {
        const blob = new Blob([content], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
    
    showDownloadProgress() {
        const progress = document.getElementById('download_progress');
        if (progress) {
            progress.classList.add('active');
        }
    }
    
    hideDownloadProgress() {
        const progress = document.getElementById('download_progress');
        if (progress) {
            progress.classList.remove('active');
        }
    }
    
    updateProgress(percent, text) {
        const progressBar = document.getElementById('progress_bar');
        const progressText = document.getElementById('progress_text');
        
        if (progressBar) {
            progressBar.style.width = percent + '%';
        }
        
        if (progressText) {
            progressText.textContent = text;
        }
    }
    
    showDownloadModal() {
        const modal = document.getElementById('download_modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    }
    
    closeDownloadModal() {
        const modal = document.getElementById('download_modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }
    
    createNewPackage() {
        this.closeDownloadModal();
        this.clearAllSelections();
    }
    
    addToDownloadHistory(packageName, agentCount) {
        const history = JSON.parse(localStorage.getItem('download_history') || '[]');
        history.unshift({
            name: packageName,
            agentCount: agentCount,
            timestamp: new Date().toISOString()
        });
        
        // Keep only last 5 downloads
        history.splice(5);
        localStorage.setItem('download_history', JSON.stringify(history));
        
        this.updateDownloadHistoryDisplay();
    }
    
    updateDownloadHistoryDisplay() {
        const history = JSON.parse(localStorage.getItem('download_history') || '[]');
        const container = document.getElementById('download_history');
        
        if (container) {
            if (history.length === 0) {
                container.innerHTML = '<p>No recent downloads</p>';
            } else {
                container.innerHTML = history.map(item => `
                    <div class="flex justify-between items-center">
                        <span>${item.name}</span>
                        <span class="text-gray-400">${item.agentCount} agents</span>
                    </div>
                `).join('');
            }
        }
    }
    
    updatePackagePreview() {
        const preview = document.getElementById('package_preview');
        const packageName = document.getElementById('package_name')?.value || 'my_ai_team';
        const includeReadme = document.getElementById('include_readme')?.checked ?? true;
        const selectedAgents = JSON.parse(localStorage.getItem('selected_agents') || '[]');
        
        if (selectedAgents.length > 0 && preview) {
            let contents = `📦 ${packageName}.zip<br>├── agents/<br>`;
            
            // Add agent files (simulated)
            for (let i = 1; i <= Math.min(selectedAgents.length, 3); i++) {
                contents += `│   ├── partner_${i}.md<br>`;
            }
            
            if (selectedAgents.length > 3) {
                contents += `│   └── ... ${selectedAgents.length - 3} more files<br>`;
            }
            
            if (includeReadme) contents += `├── README.md<br>`;
            contents += `└── package_metadata.json`;
            
            const previewContent = preview.querySelector('.font-mono');
            if (previewContent) {
                previewContent.innerHTML = contents;
            }
            
            preview.classList.remove('hidden');
        } else if (preview) {
            preview.classList.add('hidden');
        }
    }
    
    // Comparison functionality
    loadSampleComparison() {
        // Load sample agent IDs for demonstration
        const sampleIds = [1, 2, 3]; // Adjust based on your actual data
        localStorage.setItem('comparison_list', JSON.stringify(sampleIds));
        this.comparisonList = new Set(sampleIds);
        this.updateComparisonCounter();
        this.handleNavigation('/compare');
    }
    
    loadFromLocalStorage() {
        const comparisonList = JSON.parse(localStorage.getItem('comparison_list') || '[]');
        if (comparisonList.length > 0) {
            this.handleNavigation('/compare');
        } else {
            this.showToast('No agents selected for comparison', 'warning');
        }
    }
    
    clearComparison() {
        if (confirm('Are you sure you want to clear this comparison?')) {
            localStorage.removeItem('comparison_list');
            this.comparisonList.clear();
            this.updateComparisonCounter();
            this.handleNavigation('/compare');
        }
    }
    
    saveComparison() {
        if (this.comparisonList.size === 0) {
            this.showToast('No agents to save. Please add some agents to compare first.', 'warning');
            return;
        }
        
        try {
            const comparisonData = {
                agents: Array.from(this.comparisonList),
                timestamp: new Date().toISOString(),
                name: `Comparison_${new Date().toLocaleDateString().replace(/\//g, '-')}_${new Date().toLocaleTimeString().replace(/:/g, '-')}`
            };
            
            // Save to localStorage with a unique key
            const saveKey = `saved_comparison_${Date.now()}`;
            localStorage.setItem(saveKey, JSON.stringify(comparisonData));
            
            // Also update a list of all saved comparisons
            const savedComparisons = JSON.parse(localStorage.getItem('saved_comparisons_list') || '[]');
            savedComparisons.push({
                key: saveKey,
                name: comparisonData.name,
                timestamp: comparisonData.timestamp,
                agentCount: comparisonData.agents.length
            });
            
            // Keep only the last 10 comparisons
            if (savedComparisons.length > 10) {
                const oldKey = savedComparisons.shift().key;
                localStorage.removeItem(oldKey);
            }
            
            localStorage.setItem('saved_comparisons_list', JSON.stringify(savedComparisons));
            
            this.showToast(`Comparison saved as: ${comparisonData.name}`, 'success');
            
        } catch (error) {
            console.error('Failed to save comparison:', error);
            this.showToast('Failed to save comparison. Please try again.', 'error');
        }
    }
    
    // Additional methods for page initialization
    async loadComparePageData() {
        // Load comparison page data
        this.loadComparisonListFromStorage();
        this.updateComparisonCounter();
    }
    
      
    loadComparisonListFromStorage() {
        const savedComparison = localStorage.getItem('comparison_list');
        if (savedComparison) {
            try {
                this.comparisonList = new Set(JSON.parse(savedComparison));
                this.updateComparisonCounter();
            } catch (e) {
                console.error('Error loading comparison list:', e);
            }
        }
    }
    
    loadSelectionFromStorage() {
        const savedSelection = localStorage.getItem('selected_agents');
        if (savedSelection) {
            try {
                this.selectedAgents = new Set(JSON.parse(savedSelection));
                this.updateSelectionCounter();
            } catch (e) {
                console.error('Error loading selected agents:', e);
            }
        }
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
    
    // Initialize the current page based on URL
    const currentPath = window.location.pathname;
    if (currentPath !== '/') {
        app.loadPage(currentPath);
    } else {
        // Load home page content
        app.loadStats();
        app.loadRepositories();
    }
    
    // Set up package preview updates
    const packageNameInput = document.getElementById('package_name');
    const includeReadmeCheckbox = document.getElementById('include_readme');
    
    if (packageNameInput) {
        packageNameInput.addEventListener('input', () => app.updatePackagePreview());
    }
    
    if (includeReadmeCheckbox) {
        includeReadmeCheckbox.addEventListener('change', () => app.updatePackagePreview());
    }
});

// Global functions for download page
function initiateDownload() {
    if (app) {
        app.initiateDownload();
    }
}

function closeDownloadModal() {
    if (app) {
        app.closeDownloadModal();
    }
}

function createNewPackage() {
    if (app) {
        app.createNewPackage();
    }
}

function loadSampleComparison() {
    if (app) {
        app.loadSampleComparison();
    }
}

function loadFromLocalStorage() {
    if (app) {
        app.loadFromLocalStorage();
    }
}

function clearComparison() {
    if (app) {
        app.clearComparison();
    }
}

function saveComparison() {
    if (app) {
        app.saveComparison();
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SubagentGuildApp;
}