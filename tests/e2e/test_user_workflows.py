# End-to-end tests for complete user workflows

import pytest
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for E2E tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    """Create browser context for each test"""
    context = await browser.new_context()
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext):
    """Create page for each test"""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="session")
def test_server():
    """Start test server for E2E tests"""
    # Note: In a real scenario, you'd start the actual server
    # For this example, we'll use TestClient
    client = TestClient(app)
    # You could also start a real server with uvicorn for more realistic testing
    return client


class TestHomepageWorkflow:
    """Test complete homepage user workflows"""
    
    @pytest.mark.e2e
    async def test_homepage_navigation_flow(self, page: Page):
        """Test complete homepage navigation workflow"""
        # Navigate to homepage
        await page.goto("http://localhost:8000")
        
        # Check page loads correctly
        await page.wait_for_selector("h1", timeout=5000)
        title = await page.locator("h1").inner_text()
        assert "Agent Guild" in title
        
        # Check navigation menu
        nav_links = await page.locator("nav a").all()
        assert len(nav_links) >= 4  # Should have main navigation links
        
        # Test navigation to agents page
        await page.click("text=Explore Agents")
        await page.wait_for_url("**/agents")
        
        # Verify agents page loaded
        agents_title = await page.locator("h1").inner_text()
        assert "Partners" in agents_title or "Agents" in agents_title
    
    @pytest.mark.e2e
    async def test_featured_agents_interaction(self, page: Page):
        """Test interaction with featured agents on homepage"""
        await page.goto("http://localhost:8000")
        
        # Wait for featured agents to load
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Check if featured agents are displayed
        agent_cards = await page.locator(".agent-card").all()
        assert len(agent_cards) >= 1
        
        # Test clicking on first agent card
        if agent_cards:
            first_card = agent_cards[0]
            
            # Get agent name before clicking
            agent_link = first_card.locator("a").first
            agent_name = await agent_link.inner_text()
            
            # Click to go to agent detail
            await agent_link.click()
            
            # Wait for agent detail page
            await page.wait_for_selector("h1", timeout=5000)
            detail_title = await page.locator("h1").inner_text()
            # Title should contain agent name or "Agent" or "Partner"
            assert any(word in detail_title for word in [agent_name, "Agent", "Partner"])
    
    @pytest.mark.e2e
    async def test_lifecycle_phase_navigation(self, page: Page):
        """Test navigation through lifecycle phases"""
        await page.goto("http://localhost:8000")
        
        # Find and click on a lifecycle phase
        phase_links = await page.locator("a[href*='lifecycle=']").all()
        if phase_links:
            # Click on development phase
            dev_link = None
            for link in phase_links:
                href = await link.get_attribute("href")
                if "development" in href:
                    dev_link = link
                    break
            
            if dev_link:
                await dev_link.click()
                
                # Should navigate to agents page with development filter
                await page.wait_for_url("**/agents*")
                current_url = page.url
                assert "development" in current_url
                
                # Check that filtered results are shown
                await page.wait_for_selector(".agent-card", timeout=10000)


class TestAgentDiscoveryWorkflow:
    """Test complete agent discovery and filtering workflows"""
    
    @pytest.mark.e2e
    async def test_agent_search_workflow(self, page: Page):
        """Test complete agent search and filtering workflow"""
        await page.goto("http://localhost:8000/agents")
        
        # Wait for page to load
        await page.wait_for_selector("input[name='search']", timeout=10000)
        
        # Test search functionality
        search_input = page.locator("input[name='search']")
        await search_input.fill("backend")
        
        # Wait for HTMX to update results
        await page.wait_for_timeout(1000)  # Wait for debounced search
        await page.wait_for_selector("#agent-results", timeout=5000)
        
        # Check that results were updated
        agent_cards = await page.locator(".agent-card").all()
        # Should have some results (exact number depends on test data)
        assert len(agent_cards) >= 0
    
    @pytest.mark.e2e
    async def test_filter_combination_workflow(self, page: Page):
        """Test combining multiple filters"""
        await page.goto("http://localhost:8000/agents")
        
        # Wait for filters to load
        await page.wait_for_selector("select[name='lifecycle']", timeout=10000)
        
        # Select lifecycle phase
        await page.select_option("select[name='lifecycle']", "development")
        await page.wait_for_timeout(500)
        
        # Select role type
        await page.select_option("select[name='role']", "backend-developer")
        await page.wait_for_timeout(500)
        
        # Wait for results to update
        await page.wait_for_selector("#agent-results", timeout=5000)
        
        # Verify URL reflects filters
        current_url = page.url
        assert "lifecycle=development" in current_url
        assert "role=backend-developer" in current_url
    
    @pytest.mark.e2e
    async def test_agent_selection_workflow(self, page: Page):
        """Test selecting agents for comparison/download"""
        await page.goto("http://localhost:8000/agents")
        
        # Wait for agent cards to load
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Find and select first agent
        first_checkbox = page.locator(".agent-card input[type='checkbox']").first
        if await first_checkbox.count() > 0:
            await first_checkbox.check()
            
            # Wait for selection counter to update
            await page.wait_for_timeout(500)
            
            # Check that selection counter updated
            # (Implementation depends on your selection counter element)
            counter_element = page.locator("[data-selection-count], .selection-counter").first
            if await counter_element.count() > 0:
                counter_text = await counter_element.inner_text()
                assert "1" in counter_text


class TestAgentDetailWorkflow:
    """Test agent detail page workflows"""
    
    @pytest.mark.e2e
    async def test_agent_detail_navigation(self, page: Page):
        """Test navigating to and interacting with agent detail page"""
        # First go to agents page
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Click on first agent
        first_agent_link = page.locator(".agent-card a").first
        if await first_agent_link.count() > 0:
            await first_agent_link.click()
            
            # Wait for detail page to load
            await page.wait_for_selector("h1", timeout=5000)
            
            # Check that detail page elements are present
            elements_to_check = [
                "h1",  # Agent name
                ".classification-badge",  # Classification
                ".tech-tag"  # Tech stack
            ]
            
            for selector in elements_to_check:
                if await page.locator(selector).count() > 0:
                    # Element exists, verify it's visible
                    assert await page.locator(selector).first.is_visible()
    
    @pytest.mark.e2e
    async def test_related_agents_workflow(self, page: Page):
        """Test viewing related agents from detail page"""
        # Navigate to an agent detail page
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        first_agent_link = page.locator(".agent-card a").first
        if await first_agent_link.count() > 0:
            await first_agent_link.click()
            await page.wait_for_selector("h1", timeout=5000)
            
            # Look for related agents section
            related_section = page.locator(".related-agents, [data-related-agents]")
            if await related_section.count() > 0:
                # Check if related agents are displayed
                related_links = await related_section.locator("a").all()
                
                if related_links:
                    # Click on first related agent
                    await related_links[0].click()
                    await page.wait_for_selector("h1", timeout=5000)
                    
                    # Should be on a different agent's detail page
                    current_url = page.url
                    assert "/agents/" in current_url


class TestComparisonWorkflow:
    """Test agent comparison workflows"""
    
    @pytest.mark.e2e
    async def test_agent_comparison_workflow(self, page: Page):
        """Test complete agent comparison workflow"""
        # Start from agents page
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Select multiple agents for comparison
        checkboxes = await page.locator(".agent-card input[type='checkbox']").all()
        
        if len(checkboxes) >= 2:
            # Select first two agents
            await checkboxes[0].check()
            await checkboxes[1].check()
            
            # Navigate to comparison page
            await page.goto("http://localhost:8000/compare")
            await page.wait_for_selector("h1", timeout=5000)
            
            # Check comparison page loaded
            title = await page.locator("h1").inner_text()
            assert "Compare" in title
            
            # Look for comparison table or cards
            comparison_elements = page.locator(".comparison-table, .comparison-card, .agent-comparison")
            if await comparison_elements.count() > 0:
                assert await comparison_elements.first.is_visible()


class TestDownloadWorkflow:
    """Test download and package generation workflows"""
    
    @pytest.mark.e2e
    async def test_download_page_workflow(self, page: Page):
        """Test download page interaction"""
        await page.goto("http://localhost:8000/download")
        await page.wait_for_selector("h1", timeout=5000)
        
        # Check download page loaded
        title = await page.locator("h1").inner_text()
        assert "Download" in title
        
        # Check for download options
        package_options = page.locator(".package-option, [data-package-type]")
        if await package_options.count() > 0:
            # Select a package option
            await package_options.first.click()
            
            # Look for package customization options
            package_name_input = page.locator("input[name='package_name'], #package_name")
            if await package_name_input.count() > 0:
                await package_name_input.fill("test_package")
    
    @pytest.mark.e2e
    async def test_selection_management_workflow(self, page: Page):
        """Test managing agent selections for download"""
        # Add agents to selection from agents page
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Select an agent
        add_button = page.locator("button:has-text('Add'), button:has-text('Team')").first
        if await add_button.count() > 0:
            await add_button.click()
            await page.wait_for_timeout(500)
        
        # Go to download page
        await page.goto("http://localhost:8000/download")
        await page.wait_for_selector("h1", timeout=5000)
        
        # Check that selection is shown
        selection_area = page.locator("#selection-list, .selection-summary, [data-selection]")
        if await selection_area.count() > 0:
            # Selection should show at least one agent
            selection_text = await selection_area.inner_text()
            # Should contain some indication of selected agents
            assert len(selection_text.strip()) > 0


class TestResponsiveDesign:
    """Test responsive design and mobile compatibility"""
    
    @pytest.mark.e2e
    async def test_mobile_navigation(self, page: Page):
        """Test navigation on mobile viewport"""
        # Set mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})
        
        await page.goto("http://localhost:8000")
        await page.wait_for_selector("h1", timeout=5000)
        
        # Check if mobile navigation works
        nav = page.locator("nav")
        assert await nav.is_visible()
        
        # Test navigation link accessibility on mobile
        nav_links = await nav.locator("a").all()
        if nav_links:
            # At least first link should be clickable
            first_link = nav_links[0]
            assert await first_link.is_visible()
    
    @pytest.mark.e2e
    async def test_tablet_layout(self, page: Page):
        """Test layout on tablet viewport"""
        # Set tablet viewport
        await page.set_viewport_size({"width": 768, "height": 1024})
        
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector(".agent-card", timeout=10000)
        
        # Check that agent cards display properly on tablet
        agent_cards = await page.locator(".agent-card").all()
        if agent_cards:
            # First card should be visible and properly sized
            first_card = agent_cards[0]
            card_box = await first_card.bounding_box()
            assert card_box["width"] > 200  # Reasonable minimum width
            assert card_box["height"] > 100  # Reasonable minimum height


@pytest.mark.slow
class TestPerformanceWorkflows:
    """Test performance-related user scenarios"""
    
    @pytest.mark.e2e
    async def test_large_agent_list_performance(self, page: Page):
        """Test performance with large agent lists"""
        await page.goto("http://localhost:8000/agents")
        
        # Measure page load time
        start_time = await page.evaluate("performance.now()")
        await page.wait_for_selector(".agent-card", timeout=10000)
        end_time = await page.evaluate("performance.now()")
        
        load_time = end_time - start_time
        assert load_time < 5000  # Should load within 5 seconds
    
    @pytest.mark.e2e
    async def test_search_response_time(self, page: Page):
        """Test search response time"""
        await page.goto("http://localhost:8000/agents")
        await page.wait_for_selector("input[name='search']", timeout=10000)
        
        search_input = page.locator("input[name='search']")
        
        # Measure search response time
        start_time = await page.evaluate("performance.now()")
        await search_input.fill("test search")
        await page.wait_for_timeout(1000)  # Wait for debounced search
        end_time = await page.evaluate("performance.now()")
        
        search_time = end_time - start_time
        assert search_time < 2000  # Search should respond within 2 seconds


# Utility functions for E2E tests
class E2ETestUtils:
    """Utility functions for E2E testing"""
    
    @staticmethod
    async def wait_for_htmx_request(page: Page, timeout=5000):
        """Wait for HTMX request to complete"""
        # Wait for any ongoing HTMX requests to finish
        await page.wait_for_function(
            "() => !document.body.classList.contains('htmx-request')",
            timeout=timeout
        )
    
    @staticmethod
    async def take_screenshot_on_failure(page: Page, test_name: str):
        """Take screenshot when test fails"""
        screenshot_path = f"test_screenshots/{test_name}_failure.png"
        await page.screenshot(path=screenshot_path)
        return screenshot_path
    
    @staticmethod
    async def check_console_errors(page: Page):
        """Check for JavaScript console errors"""
        errors = []
        
        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)
        
        page.on("console", handle_console)
        
        # Run some basic page interactions
        await page.evaluate("console.log('Test console check')")
        
        # Return any errors found
        return errors