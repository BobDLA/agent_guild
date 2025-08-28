// Subagent Guild - Main Application
import { createClient } from '@supabase/supabase-js'

class SubagentGuildApp {
    constructor() {
        // Initialize Supabase client
        this.supabaseUrl = 'https://ndysgbprcsbulnpgdpbm.supabase.co'
        this.supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5keXNnYnByY3NidWxucGdkcGJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MDA0NjAsImV4cCI6MjA3MTk3NjQ2MH0.7TvoErb20c0lf9p_cIBDHLRmUlzbHXUTP2YKyHrTwX8'
        this.supabase = createClient(this.supabaseUrl, this.supabaseKey)
        
        // App state
        this.agents = []
        this.repositories = []
        this.selectedAgents = new Set()
        this.compareAgents = new Set()
        this.filters = {
            search: '',
            lifecycle: '',
            role: '',
            repository: '',
            page: 1,
            limit: 12,
            sort: 'name'
        }
        
        // Initialize app
        this.init()
    }

    async init() {
        try {
            // Show loading
            this.showLoading()
            
            // Load initial data
            await this.loadRepositories()
            await this.loadStats()
            await this.loadAgents()
            
            // Setup event listeners
            this.setupEventListeners()
            
            // Setup navigation
            this.setupNavigation()
            
            // Hide loading
            this.hideLoading()
            
            console.log('✅ Subagent Guild initialized successfully')
        } catch (error) {
            console.error('❌ Failed to initialize app:', error)
            this.showToast('Failed to initialize application', 'error')
            this.hideLoading()
        }
    }

    // Data loading methods
    async loadRepositories() {
        try {
            const { data, error } = await this.supabase
                .from('repositories')
                .select('*')
                .eq('is_active', true)
                .order('star_count', { ascending: false })
            
            if (error) throw error
            this.repositories = data
            this.renderRepositories()
        } catch (error) {
            console.error('Failed to load repositories:', error)
            this.showToast('Failed to load repositories', 'error')
        }
    }

    async loadStats() {
        try {
            // Get total agents
            const { count: agentCount } = await this.supabase
                .from('agents')
                .select('*', { count: 'exact', head: true })
            
            // Get total repositories
            const { count: repoCount } = await this.supabase
                .from('repositories')
                .select('*', { count: 'exact', head: true })
                .eq('is_active', true)
            
            // Get total tech stacks
            const { count: techCount } = await this.supabase
                .from('tech_stacks')
                .select('*', { count: 'exact', head: true })
            
            // Get total stars
            const { data: repos } = await this.supabase
                .from('repositories')
                .select('star_count')
                .eq('is_active', true)
            
            const totalStars = repos.reduce((sum, repo) => sum + (repo.star_count || 0), 0)
            
            // Update UI
            document.getElementById('total-agents').textContent = agentCount || 0
            document.getElementById('total-repos').textContent = repoCount || 0
            document.getElementById('total-tech').textContent = techCount || 0
            document.getElementById('total-stars').textContent = totalStars.toLocaleString()
            
        } catch (error) {
            console.error('Failed to load stats:', error)
        }
    }

    async loadAgents() {
        try {
            this.showAgentsLoading()
            
            let query = this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(name, description, star_count, language),
                    classification:classifications(lifecycle_phase, role_type, confidence_score)
                `)
            
            // Apply filters
            if (this.filters.search) {
                query = query.or(`name.ilike.%${this.filters.search}%,description.ilike.%${this.filters.search}%`)
            }
            
            if (this.filters.lifecycle) {
                query = query.filter('classification.lifecycle_phase', 'eq', this.filters.lifecycle)
            }
            
            if (this.filters.role) {
                query = query.filter('classification.role_type', 'eq', this.filters.role)
            }
            
            if (this.filters.repository) {
                query = query.eq('repository_id', this.filters.repository)
            }
            
            // Apply sorting
            const sortField = this.getSortField(this.filters.sort)
            query = query.order(sortField.field, { ascending: sortField.ascending })
            
            // Apply pagination
            const from = (this.filters.page - 1) * this.filters.limit
            const to = from + this.filters.limit - 1
            query = query.range(from, to)
            
            const { data, error, count } = await query
            
            if (error) throw error
            
            this.agents = data || []
            this.totalCount = count || 0
            this.renderAgents()
            this.renderPagination()
            
        } catch (error) {
            console.error('Failed to load agents:', error)
            this.showToast('Failed to load agents', 'error')
        } finally {
            this.hideAgentsLoading()
        }
    }

    getSortField(sortBy) {
        const sortMap = {
            'name': { field: 'name', ascending: true },
            'stars': { field: 'repository.star_count', ascending: false },
            'updated': { field: 'updated_at', ascending: false },
            'created': { field: 'created_at', ascending: false }
        }
        return sortMap[sortBy] || sortMap.name
    }

    // Rendering methods
    renderAgents() {
        const container = document.getElementById('agents-grid')
        
        if (this.agents.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <i class="fas fa-search text-4xl text-gray-400 mb-4"></i>
                    <p class="text-gray-600 mb-4">No agents found matching your criteria.</p>
                    <button onclick="app.resetFilters()" class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                        Reset Filters
                    </button>
                </div>
            `
            return
        }
        
        container.innerHTML = this.agents.map(agent => this.createAgentCard(agent)).join('')
    }

    createAgentCard(agent) {
        const classification = agent.classification || {}
        const repository = agent.repository || {}
        const isSelected = this.selectedAgents.has(agent.id)
        const isComparing = this.compareAgents.has(agent.id)
        
        return `
            <div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 ${isSelected ? 'ring-2 ring-guild-gold' : ''}">
                <div class="flex justify-between items-start mb-4">
                    <div class="flex-1">
                        <h3 class="text-lg font-semibold text-gray-900 mb-2">${agent.name}</h3>
                        <p class="text-gray-600 text-sm mb-3 line-clamp-2">${agent.description || 'No description available'}</p>
                        
                        <div class="flex flex-wrap gap-2 mb-3">
                            ${classification.lifecycle_phase ? `
                                <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                                    ${classification.lifecycle_phase}
                                </span>
                            ` : ''}
                            ${classification.role_type ? `
                                <span class="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                                    ${classification.role_type}
                                </span>
                            ` : ''}
                            ${repository.language ? `
                                <span class="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">
                                    ${repository.language}
                                </span>
                            ` : ''}
                        </div>
                        
                        <div class="flex items-center gap-4 text-sm text-gray-500">
                            ${repository.name ? `
                                <span class="flex items-center gap-1">
                                    <i class="fas fa-code-branch"></i>
                                    ${repository.name}
                                </span>
                            ` : ''}
                            ${repository.star_count ? `
                                <span class="flex items-center gap-1">
                                    <i class="fas fa-star text-yellow-500"></i>
                                    ${repository.star_count}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="flex gap-2">
                    <button 
                        onclick="app.toggleAgentSelection(${agent.id})"
                        class="flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                            isSelected 
                                ? 'bg-guild-gold text-white hover:bg-yellow-600' 
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }"
                    >
                        <i class="fas ${isSelected ? 'fa-check' : 'fa-download'} mr-1"></i>
                        ${isSelected ? 'Selected' : 'Select'}
                    </button>
                    
                    <button 
                        onclick="app.toggleAgentComparison(${agent.id})"
                        class="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                        title="Add to comparison"
                    >
                        <i class="fas fa-balance-scale ${isComparing ? 'text-primary-600' : ''}"></i>
                    </button>
                    
                    <button 
                        onclick="app.showAgentDetail(${agent.id})"
                        class="px-3 py-2 text-sm bg-primary-100 text-primary-700 rounded-md hover:bg-primary-200 transition-colors"
                        title="View details"
                    >
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </div>
        `
    }

    renderRepositories() {
        const container = document.getElementById('repositories-grid')
        
        container.innerHTML = this.repositories.map(repo => `
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-start justify-between mb-4">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-2">${repo.name}</h3>
                        <p class="text-gray-600 text-sm mb-3">${repo.description || 'No description available'}</p>
                        
                        <div class="flex items-center gap-4 text-sm text-gray-500">
                            <span class="flex items-center gap-1">
                                <i class="fas fa-star text-yellow-500"></i>
                                ${repo.star_count || 0}
                            </span>
                            ${repo.language ? `
                                <span class="flex items-center gap-1">
                                    <i class="fas fa-circle text-xs"></i>
                                    ${repo.language}
                                </span>
                            ` : ''}
                            ${repo.license ? `
                                <span class="flex items-center gap-1">
                                    <i class="fas fa-balance-scale"></i>
                                    ${repo.license}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="flex gap-2">
                    <a href="${repo.url}" target="_blank" class="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors text-center">
                        <i class="fab fa-github mr-1"></i>
                        View Repository
                    </a>
                </div>
            </div>
        `).join('')
    }

    renderPagination() {
        const container = document.getElementById('pagination')
        const totalPages = Math.ceil(this.totalCount / this.filters.limit)
        
        if (totalPages <= 1) {
            container.innerHTML = ''
            return
        }
        
        let paginationHTML = ''
        
        // Previous button
        if (this.filters.page > 1) {
            paginationHTML += `
                <button onclick="app.goToPage(${this.filters.page - 1})" class="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                    <i class="fas fa-chevron-left"></i>
                </button>
            `
        }
        
        // Page numbers
        for (let i = Math.max(1, this.filters.page - 2); i <= Math.min(totalPages, this.filters.page + 2); i++) {
            const isActive = i === this.filters.page
            paginationHTML += `
                <button onclick="app.goToPage(${i})" class="px-3 py-2 text-sm rounded-md ${
                    isActive 
                        ? 'bg-primary-600 text-white' 
                        : 'bg-white border border-gray-300 hover:bg-gray-50'
                }">
                    ${i}
                </button>
            `
        }
        
        // Next button
        if (this.filters.page < totalPages) {
            paginationHTML += `
                <button onclick="app.goToPage(${this.filters.page + 1})" class="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                    <i class="fas fa-chevron-right"></i>
                </button>
            `
        }
        
        container.innerHTML = paginationHTML
    }

    // Event handling methods
    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('quick-search')
        const searchBtn = document.getElementById('search-btn')
        
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch()
            }
        })
        
        searchBtn.addEventListener('click', () => {
            this.performSearch()
        })
        
        // Filter changes
        document.getElementById('lifecycle-filter').addEventListener('change', (e) => {
            this.filters.lifecycle = e.target.value
            this.filters.page = 1
            this.loadAgents()
        })
        
        document.getElementById('role-filter').addEventListener('change', (e) => {
            this.filters.role = e.target.value
            this.filters.page = 1
            this.loadAgents()
        })
        
        // Sort and limit changes
        document.getElementById('sort-select').addEventListener('change', (e) => {
            this.filters.sort = e.target.value
            this.loadAgents()
        })
        
        document.getElementById('limit-select').addEventListener('change', (e) => {
            this.filters.limit = parseInt(e.target.value)
            this.filters.page = 1
            this.loadAgents()
        })
        
        // Action buttons
        document.getElementById('compare-btn').addEventListener('click', () => {
            this.showComparison()
        })
        
        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadSelectedAgents()
        })
        
        // Modal close
        document.getElementById('close-modal').addEventListener('click', () => {
            this.hideAgentDetail()
        })
        
        // Click outside modal to close
        document.getElementById('agent-modal').addEventListener('click', (e) => {
            if (e.target.id === 'agent-modal') {
                this.hideAgentDetail()
            }
        })
    }

    setupNavigation() {
        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault()
                const target = document.querySelector(this.getAttribute('href'))
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    })
                }
            })
        })
    }

    // Action methods
    performSearch() {
        const searchInput = document.getElementById('quick-search')
        this.filters.search = searchInput.value.trim()
        this.filters.page = 1
        this.loadAgents()
    }

    goToPage(page) {
        this.filters.page = page
        this.loadAgents()
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    resetFilters() {
        this.filters = {
            search: '',
            lifecycle: '',
            role: '',
            repository: '',
            page: 1,
            limit: 12,
            sort: 'name'
        }
        
        // Reset form elements
        document.getElementById('quick-search').value = ''
        document.getElementById('lifecycle-filter').value = ''
        document.getElementById('role-filter').value = ''
        
        this.loadAgents()
    }

    toggleAgentSelection(agentId) {
        if (this.selectedAgents.has(agentId)) {
            this.selectedAgents.delete(agentId)
        } else {
            this.selectedAgents.add(agentId)
        }
        this.updateActionButtons()
        this.renderAgents()
    }

    toggleAgentComparison(agentId) {
        if (this.compareAgents.has(agentId)) {
            this.compareAgents.delete(agentId)
        } else {
            if (this.compareAgents.size >= 4) {
                this.showToast('Maximum 4 agents can be compared', 'warning')
                return
            }
            this.compareAgents.add(agentId)
        }
        this.updateActionButtons()
        this.renderAgents()
    }

    updateActionButtons() {
        const compareBtn = document.getElementById('compare-btn')
        const downloadBtn = document.getElementById('download-btn')
        
        compareBtn.querySelector('#compare-count').textContent = this.compareAgents.size
        downloadBtn.querySelector('#download-count').textContent = this.selectedAgents.size
        
        compareBtn.disabled = this.compareAgents.size < 2
        downloadBtn.disabled = this.selectedAgents.size === 0
    }

    async showAgentDetail(agentId) {
        try {
            const { data: agent, error } = await this.supabase
                .from('agents')
                .select(`
                    *,
                    repository:repositories(*),
                    classification:classifications(*),
                    tech_stacks:tech_stacks(*)
                `)
                .eq('id', agentId)
                .single()
            
            if (error) throw error
            
            const modal = document.getElementById('agent-modal')
            const title = document.getElementById('modal-title')
            const content = document.getElementById('modal-content')
            
            title.textContent = agent.name
            
            content.innerHTML = `
                <div class="space-y-6">
                    <div>
                        <h4 class="text-lg font-semibold mb-2">Description</h4>
                        <p class="text-gray-600">${agent.description || 'No description available'}</p>
                    </div>
                    
                    <div>
                        <h4 class="text-lg font-semibold mb-2">Repository</h4>
                        <div class="flex items-center gap-2">
                            <i class="fas fa-code-branch text-primary-600"></i>
                            <span class="font-medium">${agent.repository.name}</span>
                            <span class="text-gray-500">(${agent.repository.star_count || 0} stars)</span>
                        </div>
                        <a href="${agent.repository.url}" target="_blank" class="text-primary-600 hover:text-primary-700 text-sm">
                            View on GitHub <i class="fas fa-external-link-alt ml-1"></i>
                        </a>
                    </div>
                    
                    ${agent.classification ? `
                        <div>
                            <h4 class="text-lg font-semibold mb-2">Classification</h4>
                            <div class="flex flex-wrap gap-2">
                                <span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                                    Lifecycle: ${agent.classification.lifecycle_phase}
                                </span>
                                <span class="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                                    Role: ${agent.classification.role_type}
                                </span>
                                <span class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">
                                    Confidence: ${Math.round(agent.classification.confidence_score * 100)}%
                                </span>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${agent.tech_stacks && agent.tech_stacks.length > 0 ? `
                        <div>
                            <h4 class="text-lg font-semibold mb-2">Technology Stack</h4>
                            <div class="flex flex-wrap gap-2">
                                ${agent.tech_stacks.map(tech => `
                                    <span class="px-2 py-1 bg-gray-100 text-gray-800 rounded text-sm">
                                        ${tech.tag}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${agent.system_prompt ? `
                        <div>
                            <h4 class="text-lg font-semibold mb-2">System Prompt</h4>
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <pre class="whitespace-pre-wrap text-sm text-gray-700">${agent.system_prompt}</pre>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div>
                        <h4 class="text-lg font-semibold mb-2">Actions</h4>
                        <div class="flex gap-2">
                            <button onclick="app.toggleAgentSelection(${agent.id}); app.hideAgentDetail();" class="px-4 py-2 bg-guild-gold text-white rounded-md hover:bg-yellow-600 transition-colors">
                                <i class="fas fa-download mr-2"></i>
                                ${this.selectedAgents.has(agent.id) ? 'Remove from Selection' : 'Add to Selection'}
                            </button>
                            <button onclick="app.toggleAgentComparison(${agent.id}); app.hideAgentDetail();" class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors">
                                <i class="fas fa-balance-scale mr-2"></i>
                                ${this.compareAgents.has(agent.id) ? 'Remove from Comparison' : 'Add to Comparison'}
                            </button>
                        </div>
                    </div>
                </div>
            `
            
            modal.classList.remove('hidden')
            
        } catch (error) {
            console.error('Failed to load agent details:', error)
            this.showToast('Failed to load agent details', 'error')
        }
    }

    hideAgentDetail() {
        document.getElementById('agent-modal').classList.add('hidden')
    }

    showComparison() {
        if (this.compareAgents.size < 2) {
            this.showToast('Select at least 2 agents to compare', 'warning')
            return
        }
        
        // This would open a comparison modal or page
        this.showToast('Comparison feature coming soon!', 'info')
    }

    downloadSelectedAgents() {
        if (this.selectedAgents.size === 0) {
            this.showToast('No agents selected for download', 'warning')
            return
        }
        
        // This would trigger the download functionality
        this.showToast(`Preparing download for ${this.selectedAgents.size} agents...`, 'info')
    }

    // UI helper methods
    showLoading() {
        document.getElementById('loading').classList.remove('hidden')
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden')
    }

    showAgentsLoading() {
        document.getElementById('agents-loading').classList.remove('hidden')
        document.getElementById('agents-grid').classList.add('hidden')
        document.getElementById('agents-empty').classList.add('hidden')
    }

    hideAgentsLoading() {
        document.getElementById('agents-loading').classList.add('hidden')
        document.getElementById('agents-grid').classList.remove('hidden')
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container')
        
        const toast = document.createElement('div')
        toast.className = `mb-2 px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`
        
        const bgColor = {
            'info': 'bg-blue-500',
            'success': 'bg-green-500',
            'warning': 'bg-yellow-500',
            'error': 'bg-red-500'
        }[type] || 'bg-blue-500'
        
        const icon = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle'
        }[type] || 'fa-info-circle'
        
        toast.className += ` ${bgColor} text-white`
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${icon} mr-2"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `
        
        container.appendChild(toast)
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full')
        }, 100)
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('translate-x-full')
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove()
                }
            }, 300)
        }, 5000)
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SubagentGuildApp()
})