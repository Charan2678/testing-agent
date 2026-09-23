"""
Generated Playwright Test Case #4: TC-P3-001 Navigation and Fill
Category: FUNCTIONAL | Priority: HIGH
Target Base URL: http://127.0.0.1:3000
"""
import asyncio
from playwright.async_api import Page, expect

async def test_case_4(page: Page, base_url: str = "http://127.0.0.1:3000"):
    """Executes the test steps for TC #4."""
    page.set_default_timeout(10000)

    # Step 1: NAVIGATE on http://127.0.0.1:3000/login
    # Expected: Page loaded
    await page.goto("http://127.0.0.1:3000/login", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")

    # Step 2: FILL on input[name='username']
    # Expected: Filled
    await page.locator("input[name='username']").fill("test@example.com")

# Standalone execution helper
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await test_case_4(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
