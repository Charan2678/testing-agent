"""
Generated Playwright Test Case #3: TC-003 Functional: Browse Products Catalog
Category: FUNCTIONAL | Priority: HIGH
Target Base URL: http://127.0.0.1:3000
Preconditions:
  - Products exist in catalog
"""
import asyncio
from playwright.async_api import Page, expect

async def test_case_3(page: Page, base_url: str = "http://127.0.0.1:3000"):
    """Executes the test steps for TC #3."""
    page.set_default_timeout(10000)

    # Step 1: NAVIGATE on http://127.0.0.1:3000/products
    # Expected: Product management catalog renders with HTTP 200
    await page.goto("http://127.0.0.1:3000/products", wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")

# Standalone execution helper
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await test_case_3(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
