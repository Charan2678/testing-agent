"""
Generated Playwright Test Case #36: TC-008 Functional: Dashboard Summary Export Handler
Category: FUNCTIONAL | Priority: MEDIUM
Target Base URL: http://127.0.0.1:3000
"""
import asyncio
from playwright.async_api import Page, expect

async def test_case_36(page: Page, base_url: str = "http://127.0.0.1:3000"):
    """Executes the test steps for TC #36."""
    page.set_default_timeout(10000)

    # Step 1: NAVIGATE on http://127.0.0.1:3000/dashboard
    # Expected: 
    await page.goto("http://127.0.0.1:3000/dashboard", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")

    # Step 2: CLICK on #btn-export
    # Expected: 
    await page.locator("#btn-export").click()
    await page.wait_for_timeout(500)  # settle

# Standalone execution helper
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await test_case_36(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
